# app/adapters/inbound/api/v1/endpoints/user_access_groups_endpoint.py

"""
API endpoints for user-group and user-permission associations.

This module provides endpoints for managing user group memberships,
direct permissions, and retrieving user permissions.
"""

import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Path, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_permissions_current_user, get_session
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import (
    GroupOutput,
    UserGroupUpdate,
    UserPermissionOutput
)
from app.application.dtos.user_dto import UserGroupsOutput
from app.application.use_cases.user_group_use_cases import AsyncUserGroupService
from app.domain.exceptions import (
    ResourceNotFoundException,
    PermissionDeniedException
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/user-access-groups", tags=["User Access Groups"])


@router.post(
    "/{user_id}/groups",
    response_model=UserGroupsOutput,
    status_code=status.HTTP_200_OK,
    summary="Add User to Groups",
    description="Add a user to multiple groups. Requires superuser or 'manage_user_groups' permission."
)
async def add_user_to_groups(
        data: UserGroupUpdate,
        user_id: UUID = Path(..., description="The ID of the user"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Add a user to multiple groups.

    Args:
        data: List of group IDs to add the user to
        user_id: ID of the user
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated user with groups

    Example:
        ```
        {
          "group_ids": [1, 2, 3]
        }
        ```
    """
    try:
        service = AsyncUserGroupService(db)
        return await service.add_user_to_groups(current_user, user_id, data)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"User or groups not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error adding user to groups: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{user_id}/groups",
    response_model=UserGroupsOutput,
    status_code=status.HTTP_200_OK,
    summary="Remove User from Groups",
    description="Remove a user from multiple groups. Requires superuser or 'manage_user_groups' permission."
)
async def remove_user_from_groups(
        data: UserGroupUpdate,
        user_id: UUID = Path(..., description="The ID of the user"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Remove a user from multiple groups.

    Args:
        data: List of group IDs to remove the user from
        user_id: ID of the user
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated user with groups

    Example:
        ```
        {
          "group_ids": [1, 2, 3]
        }
        ```
    """
    try:
        service = AsyncUserGroupService(db)
        return await service.remove_user_from_groups(current_user, user_id, data)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error removing user from groups: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{user_id}/groups",
    response_model=List[GroupOutput],
    status_code=status.HTTP_200_OK,
    summary="Get User Groups",
    description="Get all groups a user belongs to. Users can view their own groups. "
                "Superuser or 'view_user_groups' permission required to view others."
)
async def get_user_groups(
        user_id: UUID = Path(..., description="The ID of the user"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get all groups a user belongs to.

    Args:
        user_id: ID of the user
        db: Database session
        current_user: Authenticated user

    Returns:
        List of groups the user belongs to
    """
    try:
        service = AsyncUserGroupService(db)
        return await service.get_user_groups(current_user, user_id)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting user groups: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{user_id}/permissions",
    response_model=UserPermissionOutput,
    status_code=status.HTTP_200_OK,
    summary="Get User Permissions",
    description="Get all permissions a user has (from groups and direct assignments). "
                "Users can view their own permissions. Superuser or 'view_user_permissions' "
                "permission required to view others."
)
async def get_user_permissions(
        user_id: UUID = Path(..., description="The ID of the user"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get all permissions a user has (from groups and direct assignments).

    Args:
        user_id: ID of the user
        db: Database session
        current_user: Authenticated user

    Returns:
        User permissions output with direct, group, and effective permissions
    """
    try:
        service = AsyncUserGroupService(db)
        return await service.get_user_permissions(current_user, user_id)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting user permissions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/{user_id}/direct-permissions",
    response_model=UserGroupsOutput,
    status_code=status.HTTP_200_OK,
    summary="Add Direct Permissions to User",
    description="Add direct permissions to a user. Requires superuser or 'manage_user_permissions' permission."
)
async def add_direct_permissions_to_user(
        user_id: UUID = Path(..., description="The ID of the user"),
        permission_ids: List[int] = Body(..., description="List of permission IDs to add"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Add direct permissions to a user.

    Args:
        user_id: ID of the user
        permission_ids: List of permission IDs to add
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated user with permissions

    Example:
        ```
        [1, 2, 3]
        ```
    """
    try:
        service = AsyncUserGroupService(db)
        return await service.add_direct_permissions_to_user(current_user, user_id, permission_ids)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"User or permissions not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error adding permissions to user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{user_id}/direct-permissions",
    response_model=UserGroupsOutput,
    status_code=status.HTTP_200_OK,
    summary="Remove Direct Permissions from User",
    description="Remove direct permissions from a user. Requires superuser or 'manage_user_permissions' permission."
)
async def remove_direct_permissions_from_user(
        user_id: UUID = Path(..., description="The ID of the user"),
        permission_ids: List[int] = Body(..., description="List of permission IDs to remove"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Remove direct permissions from a user.

    Args:
        user_id: ID of the user
        permission_ids: List of permission IDs to remove
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated user with permissions

    Example:
        ```
        [1, 2, 3]
        ```
    """
    try:
        service = AsyncUserGroupService(db)
        return await service.remove_direct_permissions_from_user(current_user, user_id, permission_ids)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error removing permissions from user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put(
    "/{user_id}/superuser",
    response_model=UserGroupsOutput,
    status_code=status.HTTP_200_OK,
    summary="Set User Superuser Status",
    description="Set a user's superuser status. Requires superuser."
)
async def set_user_superuser_status(
        user_id: UUID = Path(..., description="The ID of the user"),
        is_superuser: bool = Body(..., description="New superuser status"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Set a user's superuser status.

    Args:
        user_id: ID of the user
        is_superuser: New superuser status
        db: Database session
        current_user: Authenticated user

    Returns:
        Updated user

    Example:
        ```
        true
        ```
    """
    try:
        service = AsyncUserGroupService(db)
        return await service.set_user_superuser_status(current_user, user_id, is_superuser)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"User not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error updating superuser status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
