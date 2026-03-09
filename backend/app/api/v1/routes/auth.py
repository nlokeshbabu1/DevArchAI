"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import secrets
import structlog
import uuid

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationMember, MembershipRole, PlanType
from app.schemas.auth import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    APIKeyResponse,
)
from app.schemas.common import MessageResponse
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    require_admin,
    generate_api_key,
)
from app.core.exceptions import AuthenticationException

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def user_to_response(user: User) -> dict:
    """Convert User model to response dict with proper UUID serialization."""
    return {
        "id": str(user.id) if isinstance(user.id, uuid.UUID) else user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "has_api_key": bool(user.api_key),
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and create their organization."""
    logger.info("Register attempt", email=user_data.email, username=user_data.username)
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
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
        # Create organization first if organization_name provided
        organization = None
        if user_data.organization_name and user_data.organization_name.strip():
            org_name = user_data.organization_name.strip()
            org_slug = org_name.lower().replace(" ", "-")[:100]

            # Ensure unique slug
            counter = 1
            original_slug = org_slug
            while True:
                result = await db.execute(select(Organization).where(Organization.slug == org_slug))
                if not result.scalar_one_or_none():
                    break
                org_slug = f"{original_slug}-{counter}"
                counter += 1

            organization = Organization(
                name=org_name,
                slug=org_slug,
                plan=PlanType.FREE,
            )
            db.add(organization)
            await db.flush()  # Get organization ID
            logger.info("Organization created", name=org_name, slug=org_slug)

        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            current_org_id=organization.id if organization else None,
        )
        db.add(user)
        await db.flush()  # Get user ID
        logger.info("User created", user_id=user.id, email=user.email)

        # Create organization membership if organization exists
        if organization:
            membership = OrganizationMember(
                organization_id=organization.id,
                user_id=user.id,
                role=MembershipRole.OWNER,
                joined_at=datetime.utcnow(),
            )
            db.add(membership)
            logger.info("Organization membership created", user_id=user.id, org_id=organization.id)

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
    # Find user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
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
    await db.commit()

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
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
