"""Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import secrets

from devarchai.api.deps import get_db, get_current_user
from devarchai.models.user import User, UserRole
from devarchai.models.organization import Organization, OrganizationMember, MembershipRole, PlanType
from devarchai.schemas.auth import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    APIKeyResponse,
)
from devarchai.schemas.common import MessageResponse
from devarchai.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
)
from devarchai.core.exceptions import AuthenticationException

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user and create their first organization.

    Creates both user and organization in a single transaction.
    """
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

    # Create user and organization in transaction
    try:
        # Create organization first
        org_name = user_data.organization_name or f"{user_data.username}'s Organization"
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

        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            current_org_id=organization.id,
        )
        db.add(user)
        await db.flush()  # Get user ID

        # Create membership
        membership = OrganizationMember(
            organization_id=organization.id,
            user_id=user.id,
            role=MembershipRole.OWNER,
            joined_at=datetime.utcnow(),
        )
        db.add(membership)

        await db.commit()
        await db.refresh(user)

        return user

    except Exception as e:
        await db.rollback()
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
    return current_user


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

    return current_user


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

    refresh_token_str = auth_header.replace("Bearer ", "")
    payload = decode_token(refresh_token_str)

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
