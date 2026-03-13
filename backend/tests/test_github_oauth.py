"""GitHub OAuth authentication tests."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User

client = TestClient(app)


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

    @pytest.mark.asyncio
    async def test_github_callback_missing_code(self, db_session: AsyncSession):
        """Test GitHub callback without authorization code."""
        response = client.post(
            "/api/v1/auth/github/callback",
            json={},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Authorization code required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_github_callback_oauth_not_configured(
        self, 
        db_session: AsyncSession,
        mock_settings
    ):
        """Test GitHub callback when OAuth is not configured."""
        # Mock settings without GitHub OAuth
        mock_settings.GITHUB_CLIENT_ID = None
        mock_settings.GITHUB_CLIENT_SECRET = None
        
        with patch('app.api.v1.routes.auth.settings', mock_settings):
            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "GitHub OAuth not configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_github_callback_new_user(
        self,
        db_session: AsyncSession,
        mock_github_token_response,
        mock_github_user_response,
        mock_github_emails_response,
        mock_settings
    ):
        """Test GitHub OAuth for a new user."""
        # Mock GitHub API responses
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            # Mock token exchange
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_github_token_response
            
            # Mock user info
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_github_user_response
            
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
            assert data["user"]["github_id"] == "12345678"
            
            # Verify user was created in database
            result = await db_session.execute(
                select(User).where(User.email == "test@example.com")
            )
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.github_id == "12345678"
            assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_github_callback_existing_user(
        self,
        db_session: AsyncSession,
        mock_github_token_response,
        mock_github_user_response,
        mock_settings
    ):
        """Test GitHub OAuth for an existing user."""
        # Create user first
        existing_user = User(
            email="existing@example.com",
            username="existinguser",
            hashed_password="",
            github_id=None,
        )
        db_session.add(existing_user)
        await db_session.commit()
        
        # Update mock to return existing user's email
        mock_github_user_response["email"] = "existing@example.com"
        
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_github_token_response
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_github_user_response
            
            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            assert data["user"]["email"] == "existing@example.com"
            
            # Verify user was updated with GitHub info
            await db_session.refresh(existing_user)
            assert existing_user.github_id == "12345678"

    @pytest.mark.asyncio
    async def test_github_callback_token_exchange_failure(
        self,
        db_session: AsyncSession,
        mock_settings
    ):
        """Test GitHub callback when token exchange fails."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value.status_code = 400
            mock_post.return_value.json.return_value = {"error": "invalid_code"}
            
            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "invalid_code"},
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Failed to exchange authorization code" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_github_callback_user_info_failure(
        self,
        db_session: AsyncSession,
        mock_github_token_response,
        mock_settings
    ):
        """Test GitHub callback when user info fetch fails."""
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_github_token_response
            mock_get.return_value.status_code = 401
            
            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Failed to fetch GitHub user info" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_github_callback_no_email(
        self,
        db_session: AsyncSession,
        mock_github_token_response,
        mock_settings
    ):
        """Test GitHub callback when no email is found."""
        github_user_no_email = {
            "login": "testuser",
            "id": 12345678,
            "email": None,
            "name": "Test User",
        }
        
        with patch('httpx.AsyncClient.post') as mock_post, \
             patch('httpx.AsyncClient.get') as mock_get:
            
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_github_token_response
            
            # First call for user info (no email)
            # Second call for emails (empty list)
            mock_get.side_effect = [
                MagicMock(status_code=200, json=lambda: github_user_no_email),
                MagicMock(status_code=200, json=lambda: []),
            ]
            
            response = client.post(
                "/api/v1/auth/github/callback",
                json={"code": "mock_code_123"},
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "No email found in GitHub account" in response.json()["detail"]


class TestGitHubOAuthIntegration:
    """Integration tests for GitHub OAuth (requires GitHub API access)."""

    @pytest.mark.skip(reason="Requires real GitHub OAuth credentials")
    @pytest.mark.asyncio
    async def test_full_github_oauth_flow(self, db_session: AsyncSession):
        """Test complete GitHub OAuth flow with real GitHub API."""
        # This test requires:
        # 1. GITHUB_CLIENT_ID environment variable
        # 2. GITHUB_CLIENT_SECRET environment variable
        # 3. Manual OAuth authorization to get a real code
        
        pytest.skip("Skipping integration test - requires real GitHub credentials")
