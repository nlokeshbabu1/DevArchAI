"""GitHub OAuth authentication tests."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User

client = TestClient(app, raise_server_exceptions=False)


def _error_message(response):
    """Extract error message from the app's standard error response format."""
    data = response.json()
    if "detail" in data:
        return data["detail"]
    if "error" in data and isinstance(data["error"], dict):
        return data["error"].get("message", "")
    return ""


class TestGitHubOAuth:
    """Test GitHub OAuth authentication flow."""

    @pytest.fixture
    def mock_github_token_response(self):
        """Mock GitHub token exchange response."""
        return {
            "access_token": "gho_mock_access_token_12345",
            "token_type": "bearer",
            "scope": "user:email",
        }

    @pytest.fixture
    def mock_github_user_response(self):
        """Mock GitHub user info response."""
        return {
            "login": "testuser",
            "id": 12345678,
            "email": "test@example.com",
            "name": "Test User",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4",
        }

    @pytest.fixture
    def mock_github_emails_response(self):
        """Mock GitHub emails response."""
        return [
            {
                "email": "test@example.com",
                "primary": True,
                "verified": True,
                "visibility": "public",
            }
        ]

    def test_github_callback_missing_code(self):
        """Test GitHub callback without authorization code."""
        response = client.post(
            "/api/v1/auth/github/callback",
            json={},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Authorization code required" in _error_message(response)

    def test_github_callback_oauth_not_configured(self, mock_settings):
        """Test GitHub callback when OAuth is not configured."""
        mock_settings.GITHUB_CLIENT_ID = None
        mock_settings.GITHUB_CLIENT_SECRET = None

        with patch('app.api.v1.routes.auth.settings', mock_settings):
            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "GitHub OAuth not configured" in _error_message(response)

    def test_github_callback_new_user(
        self,
        mock_github_token_response,
        mock_github_user_response,
        mock_github_emails_response,
        mock_settings,
    ):
        """Test GitHub OAuth for a new user."""
        mock_settings.GITHUB_CLIENT_ID = "test_client_id"
        mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_github_token_response

        mock_get_user_response = MagicMock()
        mock_get_user_response.status_code = 200
        mock_get_user_response.json.return_value = mock_github_user_response

        mock_async_client = MagicMock()
        mock_async_client.post = AsyncMock(return_value=mock_post_response)
        mock_async_client.get = AsyncMock(return_value=mock_get_user_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch('app.api.v1.routes.auth.settings', mock_settings), \
             patch('httpx.AsyncClient', return_value=mock_async_client):

            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            assert "access_token" in data
            assert "refresh_token" in data
            assert "user" in data
            assert data["user"]["email"] == "test@example.com"
            assert data["user"]["username"] == "testuser"
            assert data["user"]["has_github"] is True

    def test_github_callback_existing_user(
        self,
        mock_github_token_response,
        mock_github_user_response,
        mock_settings,
    ):
        """Test GitHub OAuth for an existing user.

        Uses the same email as the new_user test so the user already exists
        in the test database, and the callback updates rather than creates.
        """
        mock_settings.GITHUB_CLIENT_ID = "test_client_id"
        mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"

        mock_get_user_response = MagicMock()
        mock_get_user_response.status_code = 200
        mock_get_user_response.json.return_value = {
            **mock_github_user_response,
            "email": "test@example.com",
        }

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_github_token_response

        mock_async_client = MagicMock()
        mock_async_client.post = AsyncMock(return_value=mock_post_response)
        mock_async_client.get = AsyncMock(return_value=mock_get_user_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch('app.api.v1.routes.auth.settings', mock_settings), \
             patch('httpx.AsyncClient', return_value=mock_async_client):

            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user"]["email"] == "test@example.com"
            assert data["user"]["has_github"] is True

    def test_github_callback_token_exchange_failure(self, mock_settings):
        """Test GitHub callback when token exchange fails."""
        mock_settings.GITHUB_CLIENT_ID = "test_client_id"
        mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"

        mock_post_response = MagicMock()
        mock_post_response.status_code = 400
        mock_post_response.json.return_value = {"error": "invalid_code"}

        mock_async_client = MagicMock()
        mock_async_client.post = AsyncMock(return_value=mock_post_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch('app.api.v1.routes.auth.settings', mock_settings), \
             patch('httpx.AsyncClient', return_value=mock_async_client):

            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "invalid_code"},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Failed to exchange authorization code" in _error_message(response)

    def test_github_callback_user_info_failure(
        self,
        mock_github_token_response,
        mock_settings,
    ):
        """Test GitHub callback when user info fetch fails."""
        mock_settings.GITHUB_CLIENT_ID = "test_client_id"
        mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_github_token_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 401

        mock_async_client = MagicMock()
        mock_async_client.post = AsyncMock(return_value=mock_post_response)
        mock_async_client.get = AsyncMock(return_value=mock_get_response)
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch('app.api.v1.routes.auth.settings', mock_settings), \
             patch('httpx.AsyncClient', return_value=mock_async_client):

            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Failed to fetch GitHub user info" in _error_message(response)

    def test_github_callback_no_email(
        self,
        mock_github_token_response,
        mock_settings,
    ):
        """Test GitHub callback when no email is found."""
        mock_settings.GITHUB_CLIENT_ID = "test_client_id"
        mock_settings.GITHUB_CLIENT_SECRET = "test_client_secret"

        github_user_no_email = {
            "login": "testuser",
            "id": 12345678,
            "email": None,
            "name": "Test User",
        }

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = mock_github_token_response

        mock_get_user_response = MagicMock()
        mock_get_user_response.status_code = 200
        mock_get_user_response.json.return_value = github_user_no_email

        mock_get_emails_response = MagicMock()
        mock_get_emails_response.status_code = 200
        mock_get_emails_response.json.return_value = []

        mock_async_client = MagicMock()
        mock_async_client.post = AsyncMock(return_value=mock_post_response)
        mock_async_client.get = AsyncMock(side_effect=[mock_get_user_response, mock_get_emails_response])
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)

        with patch('app.api.v1.routes.auth.settings', mock_settings), \
             patch('httpx.AsyncClient', return_value=mock_async_client):

            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "No email found in GitHub account" in _error_message(response)


class TestGitHubOAuthIntegration:
    """Integration tests for GitHub OAuth (requires GitHub API access)."""

    @pytest.mark.skip(reason="Requires real GitHub OAuth credentials")
    def test_full_github_oauth_flow(self, db_session):
        """Test complete GitHub OAuth flow with real GitHub API."""
        pytest.skip("Skipping integration test - requires real GitHub credentials")
