# app/adapters/inbound/api/v1/dependencies/permission_deps.py

"""
Permission dependencies for API endpoints.

This module provides FastAPI dependencies for checking user permissions,
allowing role-based access control to API endpoints.
"""

import logging
from typing import List, Optional, Callable, Any
from fastapi import Depends, HTTPException, status

from app.adapters.inbound.api.deps import get_permissions_current_user
from app.adapters.outbound.persistence.models.user_group.user_model import User

logger = logging.getLogger(__name__)


def require_permissions(required_permissions: List[str], require_all: bool = False):
    """
    Dependency for checking if a user has the required permissions.

    Args:
        required_permissions: List of permission codenames required
        require_all: If True, the user must have all permissions. If False, any one is sufficient.

    Returns:
        Dependency function that returns the user if authorized

    Raises:
        HTTPException: If the user doesn't have the required permissions
    """

    async def check_permissions(current_user: User = Depends(get_permissions_current_user)) -> User:
        # Superusers can do anything
        if current_user.is_superuser:
            return current_user

        # Check required permissions
        if require_all:
            # User must have all permissions
            missing_permissions = []
            for permission in required_permissions:
                if not current_user.has_permission(permission):
                    missing_permissions.append(permission)

            if missing_permissions:
                logger.warning(
                    f"User {current_user.email} missing required permissions: {missing_permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You need all of these permissions: {required_permissions}"
                )
        else:
            # User needs at least one of the permissions
            has_any = False
            for permission in required_permissions:
                if current_user.has_permission(permission):
                    has_any = True
                    break

            if not has_any:
                logger.warning(
                    f"User {current_user.email} has none of the required permissions: {required_permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You need at least one of these permissions: {required_permissions}"
                )

        return current_user

    return check_permissions


def require_any_permission(*permissions: str) -> Callable:
    """
    Require any one of the specified permissions.

    Args:
        *permissions: Permission codenames, at least one of which is required

    Returns:
        Dependency function that returns the user if authorized
    """
    return require_permissions(list(permissions), require_all=False)


def require_all_permissions(*permissions: str) -> Callable:
    """
    Require all of the specified permissions.

    Args:
        *permissions: Permission codenames, all of which are required

    Returns:
        Dependency function that returns the user if authorized
    """
    return require_permissions(list(permissions), require_all=True)


def require_superuser(current_user: User = Depends(get_permissions_current_user)) -> User:
    """
    Require that the user is a superuser.

    Args:
        current_user: The authenticated user

    Returns:
        The user if they are a superuser

    Raises:
        HTTPException: If the user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser {current_user.email} attempted to access superuser-only endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires superuser privileges"
        )

    return current_user


def allow_own_or_require_permission(permission: str, user_id_param: str = "user_id"):
    """
    Allow a user to access their own resources, or require a specific permission.

    Args:
        permission: Permission required to access other users' resources
        user_id_param: Name of the path parameter that contains the user ID

    Returns:
        Dependency function that returns the user if authorized
    """

    async def check_permission(
            current_user: User = Depends(get_permissions_current_user),
            **path_params: Any
    ) -> User:
        # Extract the user ID from path parameters
        target_user_id = str(path_params.get(user_id_param, ""))

        # Allow access to own resources
        if target_user_id and str(current_user.id) == target_user_id:
            return current_user

        # Superusers can access anything
        if current_user.is_superuser:
            return current_user

        # Other users need the specific permission
        if current_user.has_permission(permission):
            return current_user

        logger.warning(
            f"User {current_user.email} attempted to access resource for user {target_user_id} "
            f"without {permission} permission"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have permission to access this resource"
        )

    return check_permission
