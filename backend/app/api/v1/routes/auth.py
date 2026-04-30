"""Authentication routes."""

import uuid
from datetime import datetime

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_user_email,
    encrypt_user_email,
    generate_api_key,
    get_current_user,
    get_password_hash,
    hash_email,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    APIKeyResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.schemas.common import MessageResponse
from app.services.organization_provisioning import ensure_user_organization_membership

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def user_to_response(user: User) -> dict:
    """Convert User model to response dict with proper UUID serialization."""
    # Decrypt email for response
    email = decrypt_user_email(user.email_encrypted)
    
    return {
        "id": str(user.id) if isinstance(user.id, uuid.UUID) else user.id,
        "email": email,
        "username": user.username,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "has_api_key": bool(user.api_key),
        "plan": user.subscription_plan if hasattr(user, 'subscription_plan') else "free",
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and create their organization."""
    logger.info("Register attempt", username=user_data.username)

    # Check if email already exists (using hash)
    email_hash = hash_email(user_data.email)
    result = await db.execute(select(User).where(User.email_hash == email_hash))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    try:
        # Encrypt email and create hash
        email_encrypted, email_hash = encrypt_user_email(user_data.email)

        # Create user with encrypted email
        user = User(
            email_encrypted=email_encrypted,
            email_hash=email_hash,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            country=user_data.country or "US",
        )
        db.add(user)
        await db.flush()  # Get user ID
        logger.info("User created", user_id=user.id)

        await ensure_user_organization_membership(
            db,
            user,
            organization_name=user_data.organization_name,
        )

        await db.commit()
        await db.refresh(user)
        logger.info("Registration completed", user_id=user.id)

        # Return dict directly to avoid Pydantic validation issues
        return user_to_response(user)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Registration failed", error=str(e), email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )

@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    # Find user by email hash
    email_hash = hash_email(credentials.email)
    result = await db.execute(select(User).where(User.email_hash == email_hash))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last login
    user.last_login_at = datetime.utcnow()
    await ensure_user_organization_membership(db, user)
    await db.commit()

    # Decrypt email for token
    email = decrypt_user_email(user.email_encrypted)
    
    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/github/url")
async def get_github_oauth_url(redirect_uri: str | None = None):
    """
    Get GitHub OAuth authorization URL.

    Returns the URL to redirect users to for GitHub OAuth authentication.
    Uses redirect_uri from query param if provided, otherwise uses settings.
    """
    if not settings.GITHUB_CLIENT_ID:
        # Return a mock URL for development/testing
        # In production, this should return actual OAuth URL
        return {
            "oauth_url": None,
            "error": "GitHub OAuth not configured",
            "message": "Please use email/password authentication"
        }

    # Use redirect_uri from query param if provided, otherwise use settings
    final_redirect_uri = redirect_uri or settings.GITHUB_REDIRECT_URI

    # Build OAuth URL
    oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=user:email%20read:user%20repo"
    )

    logger.info("Generated GitHub OAuth URL", redirect_uri=final_redirect_uri)
    return {"oauth_url": oauth_url}


@router.post("/github/callback")
async def github_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    GitHub OAuth callback endpoint.

    Exchanges GitHub authorization code for access token,
    gets user info, and creates/updates user in database.
    """
    try:
        # Get authorization code from request
        data = await request.json()
        code = data.get("code")

        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Authorization code required",
            )

        # Validate GitHub OAuth settings
        if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
            logger.error("GitHub OAuth not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GitHub OAuth not configured on server",
            )

        # Exchange code for access token
        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data=token_data,
                headers={"Accept": "application/json"},
                timeout=10.0,
            )

            if token_response.status_code != 200:
                logger.error("GitHub token exchange failed", status=token_response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code",
                )

            token_json = token_response.json()
            access_token = token_json.get("access_token")

            if not access_token:
                logger.error("No access token in GitHub response", response=token_json)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No access token received from GitHub",
                )

            # Get user info from GitHub
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=10.0,
            )

            if user_response.status_code != 200:
                logger.error("GitHub user info fetch failed", status=user_response.status_code)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch GitHub user info",
                )

            github_user = user_response.json()

            # Extract user information
            github_id = str(github_user.get("id"))
            email = github_user.get("email")
            username = github_user.get("login")
            full_name = github_user.get("name", "")
            avatar_url = github_user.get("avatar_url", "")

            # If no email from GitHub, fetch it
            if not email:
                emails_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=10.0,
                )

                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    # Get primary email
                    for email_data in emails:
                        if email_data.get("primary"):
                            email = email_data.get("email")
                            break

            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No email found in GitHub account",
                )

            # Find or create user in database using email hash
            email_hash = hash_email(email)
            result = await db.execute(select(User).where(User.email_hash == email_hash))
            user = result.scalar_one_or_none()

            if not user:
                # Encrypt email and create hash
                email_encrypted, email_hash = encrypt_user_email(email)

                # Create new user
                user = User(
                    email_encrypted=email_encrypted,
                    email_hash=email_hash,
                    username=username or email.split("@")[0],
                    hashed_password="",  # No password for OAuth users
                    full_name=full_name or "",
                    avatar_url=avatar_url or "",
                    github_id=github_id,
                    github_login=username,  # Store GitHub username for webhook lookups
                    github_access_token=access_token,  # Store GitHub token for API access
                    is_verified=True,  # GitHub emails are verified
                )
                db.add(user)
                await db.flush()
                logger.info("User created from GitHub OAuth", user_id=user.id)
            else:
                # Update existing user with GitHub info
                user.github_id = github_id
                user.github_login = username  # Store/update GitHub username
                user.github_access_token = access_token  # Update token
                if avatar_url:
                    user.avatar_url = avatar_url
                if full_name and not user.full_name:
                    user.full_name = full_name

            # Update last login
            user.last_login_at = datetime.utcnow()
            await ensure_user_organization_membership(db, user)
            await db.commit()
            await db.refresh(user)

            # Decrypt email for JWT token
            decrypted_email = decrypt_user_email(user.email_encrypted)
            
            # Generate JWT tokens
            access_token_jwt = create_access_token(data={"sub": str(user.id), "email": decrypted_email})
            refresh_token_jwt = create_refresh_token(data={"sub": str(user.id)})

            logger.info("GitHub OAuth successful", user_id=user.id)

            return {
                "access_token": access_token_jwt,
                "refresh_token": refresh_token_jwt,
                "token_type": "bearer",
                "user": user_to_response(user),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GitHub OAuth callback failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub OAuth failed: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information."""
    return user_to_response(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    # Update fields
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.avatar_url is not None:
        current_user.avatar_url = user_data.avatar_url

    # Update password if provided
    if user_data.new_password:
        if not user_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password required to set new password",
            )

        if not verify_password(user_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        current_user.hashed_password = get_password_hash(user_data.new_password)

    await db.commit()
    await db.refresh(current_user)

    return user_to_response(current_user)


@router.post("/api-key", response_model=APIKeyResponse)
async def create_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key for the current user."""
    api_key, prefix = generate_api_key()

    current_user.api_key = api_key
    current_user.api_key_prefix = prefix

    await db.commit()

    return APIKeyResponse(
        api_key=api_key,
        api_key_prefix=prefix,
        created_at=datetime.utcnow(),
    )


@router.delete("/api-key", response_model=MessageResponse)
async def revoke_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current API key."""
    current_user.api_key = None
    current_user.api_key_prefix = None

    await db.commit()

    return MessageResponse(message="API key revoked successfully")


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
        )

    refresh_token = auth_header.replace("Bearer ", "")
    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Get user
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Generate new tokens
    new_access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )
