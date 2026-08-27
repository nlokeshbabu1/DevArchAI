"""Security regression tests for authentication configuration.

These tests ensure security-critical configuration defaults are correct
and have not been accidentally changed.
"""

import pytest


class TestSecurityConfigDefaults:
    """Verify security configuration defaults are production-safe."""

    def test_access_token_expire_minutes(self):
        """Access token expiry must be <= 15 minutes."""
        from app.config import settings
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 15, (
            f"Access token expiry {settings.ACCESS_TOKEN_EXPIRE_MINUTES}min exceeds 15min limit"
        )

    def test_refresh_token_expire_days(self):
        """Refresh token expiry must be <= 7 days."""
        from app.config import settings
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS <= 7, (
            f"Refresh token expiry {settings.REFRESH_TOKEN_EXPIRE_DAYS}days exceeds 7day limit"
        )

    def test_refresh_token_storage_mode_cookie_only(self):
        """Default storage mode must be cookie_only (not hybrid/legacy)."""
        from app.config import settings
        assert settings.AUTH_REFRESH_TOKEN_STORAGE_MODE == "cookie_only", (
            f"Storage mode is {settings.AUTH_REFRESH_TOKEN_STORAGE_MODE}, expected cookie_only"
        )

    def test_cookie_path_restricted(self):
        """Refresh cookie path must be restricted to /api/v1/auth/refresh."""
        from app.config import settings
        assert settings.COOKIE_PATH == "/api/v1/auth/refresh", (
            f"Cookie path is {settings.COOKIE_PATH}, expected /api/v1/auth/refresh"
        )

    def test_cookie_samesite_lax(self):
        """Refresh cookie SameSite must be Lax."""
        from app.config import settings
        assert settings.COOKIE_SAMESITE == "Lax", (
            f"Cookie SameSite is {settings.COOKIE_SAMESITE}, expected Lax"
        )

    def test_jwt_issuer_set(self):
        """JWT tokens must have an issuer claim."""
        from app.core.security import JWT_ISSUER
        assert JWT_ISSUER == "devarchai", f"JWT issuer is {JWT_ISSUER}, expected devarchai"

    def test_jwt_audience_set(self):
        """JWT tokens must have an audience claim."""
        from app.core.security import JWT_AUDIENCE
        assert JWT_AUDIENCE == "devarchai-api", f"JWT audience is {JWT_AUDIENCE}, expected devarchai-api"


class TestTokenClaims:
    """Verify JWT tokens include security claims."""

    def test_access_token_has_issuer(self):
        """Access tokens must include iss claim."""
        from app.core.security import create_access_token, decode_token
        token = create_access_token({"sub": "test@test.com", "user_id": "1"})
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("iss") == "devarchai"

    def test_access_token_has_audience(self):
        """Access tokens must include aud claim."""
        from app.core.security import create_access_token, decode_token
        token = create_access_token({"sub": "test@test.com", "user_id": "1"})
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("aud") == "devarchai-api"

    def test_refresh_token_has_issuer(self):
        """Refresh tokens must include iss claim."""
        from app.core.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "test@test.com", "user_id": "1"})
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("iss") == "devarchai"

    def test_refresh_token_has_audience(self):
        """Refresh tokens must include aud claim."""
        from app.core.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "test@test.com", "user_id": "1"})
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("aud") == "devarchai-api"

    def test_token_rejects_wrong_issuer(self):
        """Tokens with wrong issuer should fail validation."""
        from app.core.security import decode_token
        import jwt
        from app.config import settings

        # Create a token manually with wrong issuer
        wrong_token = jwt.encode(
            {"sub": "test@test.com", "iss": "attacker", "aud": "devarchai-api", "exp": 9999999999},
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        result = decode_token(wrong_token)
        assert result is None, "Token with wrong issuer should be rejected"

    def test_token_rejects_wrong_audience(self):
        """Tokens with wrong audience should fail validation."""
        from app.core.security import decode_token
        import jwt
        from app.config import settings

        wrong_token = jwt.encode(
            {"sub": "test@test.com", "iss": "devarchai", "aud": "attacker", "exp": 9999999999},
            settings.SECRET_KEY,
            algorithm="HS256",
        )
        result = decode_token(wrong_token)
        assert result is None, "Token with wrong audience should be rejected"


class TestTokenFamilyTracking:
    """Verify token family column exists for reuse detection."""

    def test_user_session_has_token_family(self):
        """UserSession model must have token_family column."""
        from app.models.settings import UserSession
        assert hasattr(UserSession, 'token_family'), "UserSession missing token_family column"

    def test_token_family_is_nullable(self):
        """Token family should be nullable for backward compatibility."""
        from app.models.settings import UserSession
        col = UserSession.__table__.c.token_family
        assert col.nullable is True, "token_family should be nullable"
