"""Enterprise RBAC — roles, permissions, and enforcement."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from enum import Enum
from functools import wraps
from typing import Any

import structlog
from fastapi import Depends, HTTPException, status

from app.models.user import User

logger = structlog.get_logger(__name__)


class Permission(str, Enum):
    SCAN_CREATE = "scan:create"
    SCAN_VIEW = "scan:view"
    AWS_CONNECT = "aws:connect"
    REPORT_DOWNLOAD = "report:download"
    FINDINGS_RESOLVE = "findings:resolve"
    SETTINGS_UPDATE = "settings:update"
    USERS_MANAGE = "users:manage"
    ORG_MANAGE = "org:manage"
    AUDIT_VIEW = "audit:view"
    BILLING_MANAGE = "billing:manage"
    API_KEYS_MANAGE = "api-keys:manage"
    SESSIONS_MANAGE = "sessions:manage"
    INTEGRATIONS_MANAGE = "integrations:manage"


class SystemRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    SECURITY_ADMIN = "security_admin"
    DEVOPS_ENGINEER = "devops_engineer"
    AUDITOR = "auditor"
    READONLY = "readonly"


ROLE_PERMISSIONS: dict[SystemRole, set[Permission]] = {
    SystemRole.SUPER_ADMIN: set(Permission),
    SystemRole.ORG_ADMIN: {
        Permission.SCAN_CREATE,
        Permission.SCAN_VIEW,
        Permission.AWS_CONNECT,
        Permission.REPORT_DOWNLOAD,
        Permission.FINDINGS_RESOLVE,
        Permission.SETTINGS_UPDATE,
        Permission.USERS_MANAGE,
        Permission.ORG_MANAGE,
        Permission.BILLING_MANAGE,
        Permission.API_KEYS_MANAGE,
        Permission.SESSIONS_MANAGE,
        Permission.INTEGRATIONS_MANAGE,
    },
    SystemRole.SECURITY_ADMIN: {
        Permission.SCAN_CREATE,
        Permission.SCAN_VIEW,
        Permission.REPORT_DOWNLOAD,
        Permission.FINDINGS_RESOLVE,
        Permission.AUDIT_VIEW,
        Permission.SESSIONS_MANAGE,
    },
    SystemRole.DEVOPS_ENGINEER: {
        Permission.SCAN_CREATE,
        Permission.SCAN_VIEW,
        Permission.AWS_CONNECT,
        Permission.REPORT_DOWNLOAD,
        Permission.FINDINGS_RESOLVE,
        Permission.INTEGRATIONS_MANAGE,
    },
    SystemRole.AUDITOR: {
        Permission.SCAN_VIEW,
        Permission.REPORT_DOWNLOAD,
        Permission.AUDIT_VIEW,
    },
    SystemRole.READONLY: {
        Permission.SCAN_VIEW,
        Permission.REPORT_DOWNLOAD,
    },
}


LEGACY_ROLE_MAP: dict[str, SystemRole] = {
    "super_admin": SystemRole.SUPER_ADMIN,
    "admin": SystemRole.ORG_ADMIN,
    "enterprise": SystemRole.ORG_ADMIN,
    "user": SystemRole.DEVOPS_ENGINEER,
}


def get_user_permissions(user: User) -> set[Permission]:
    legacy_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    system_role = LEGACY_ROLE_MAP.get(legacy_role, SystemRole.READONLY)
    return ROLE_PERMISSIONS.get(system_role, set())


def require_permission(permission: Permission) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user: User | None = kwargs.get("current_user")
            if user is None:
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            perms = get_user_permissions(user)
            if permission not in perms:
                logger.warning(
                    "Permission denied",
                    user_id=str(user.id),
                    role=user.role.value if hasattr(user.role, "value") else str(user.role),
                    required=permission.value,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def check_permission(user: User, permission: Permission) -> None:
    if permission not in get_user_permissions(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: {permission.value}",
        )


def require_any_permission(permissions: Sequence[Permission]) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user: User | None = kwargs.get("current_user")
            if user is None:
                for arg in args:
                    if isinstance(arg, User):
                        user = arg
                        break
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            user_perms = get_user_permissions(user)
            if not any(p in user_perms for p in permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def permissions_dependency(required: Sequence[Permission]):
    async def _perm_checker(current_user: User = Depends(get_current_user_dep)) -> User:
        user_perms = get_user_permissions(current_user)
        if not all(p in user_perms for p in required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _perm_checker


from app.core.security import get_current_user as get_current_user_dep
