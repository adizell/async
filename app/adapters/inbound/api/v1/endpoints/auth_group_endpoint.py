# app/adapters/inbound/api/v1/endpoints/auth_group_endpoint.py

"""
API endpoints for group management.

This module provides endpoints for creating, reading, updating, and deleting groups,
as well as managing group permissions.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi_pagination import Params, Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_permissions_current_user, get_session
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import (
    GroupCreate,
    GroupUpdate,
    GroupOutput,
    GroupPermissionUpdate, PermissionOutput
)
from app.application.use_cases.group_use_cases import AsyncGroupService
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    PermissionDeniedException
)
from app.shared.utils.pagination import pagination_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth-groups", tags=["Auth Groups"])


@router.post(
    "",
    response_model=GroupOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Create Group",
    description="Create a new permission group. Requires superuser or 'manage_groups' permission."
)
async def create_group(
        data: GroupCreate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Create a new permission group.

    Args:
        data: Group creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        The created group

    Example:
        ```
        {
          "name": "editors"
        }
        ```
    """
    try:
        service = AsyncGroupService(db)
        return await service.create_group(current_user, data)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceAlreadyExistsException as e:
        logger.warning(f"Group already exists: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except Exception as e:
        logger.exception(f"Error creating group: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "",
    response_model=Page[GroupOutput],
    status_code=status.HTTP_200_OK,
    summary="List Groups",
    description="List all permission groups with pagination."
)
async def list_groups(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user),
        params: Params = Depends(pagination_params)
):
    """
    List all permission groups with pagination.

    Args:
        db: Database session
        current_user: Authenticated user
        params: Pagination parameters

    Returns:
        Paginated list of groups
    """
    try:
        service = AsyncGroupService(db)
        return await service.list_groups(current_user, params)

    except Exception as e:
        logger.exception(f"Error listing groups: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{group_id}",
    response_model=GroupOutput,
    status_code=status.HTTP_200_OK,
    summary="Get Group",
    description="Get a specific group by ID."
)
async def get_group(
        group_id: int = Path(..., gt=0, description="The ID of the group to get"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get a specific group by ID.

    Args:
        group_id: ID of the group
        db: Database session
        current_user: Authenticated user

    Returns:
        The requested group
    """
    try:
        service = AsyncGroupService(db)
        return await service.get_group(group_id)

    except ResourceNotFoundException as e:
        logger.warning(f"Group not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting group: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put(
    "/{group_id}",
    response_model=GroupOutput,
    status_code=status.HTTP_200_OK,
    summary="Update Group",
    description="Update a group's information. Requires superuser or 'manage_groups' permission."
)
async def update_group(
        data: GroupUpdate,
        group_id: int = Path(..., gt=0, description="The ID of the group to update"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Update a group's information.

    Args:
        data: Updated group data
        group_id: ID of the group
        db: Database session
        current_user: Authenticated user

    Returns:
        The updated group

    Example:
        ```
        {
          "name": "senior_editors"
        }
        ```
    """
    try:
        service = AsyncGroupService(db)
        return await service.update_group(current_user, group_id, data)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Group not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except ResourceAlreadyExistsException as e:
        logger.warning(f"Group name already exists: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except Exception as e:
        logger.exception(f"Error updating group: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Group",
    description="Delete a group. Requires superuser or 'manage_groups' permission."
)
async def delete_group(
        group_id: int = Path(..., gt=0, description="The ID of the group to delete"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Delete a group.

    Args:
        group_id: ID of the group
        db: Database session
        current_user: Authenticated user

    Returns:
        Success message
    """
    try:
        service = AsyncGroupService(db)
        return await service.delete_group(current_user, group_id)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Group not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error deleting group: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{group_id}/permissions",
    response_model=List[PermissionOutput],
    status_code=status.HTTP_200_OK,
    summary="Get Group Permissions",
    description="Get all permissions for a specific group."
)
async def get_group_permissions(
        group_id: int = Path(..., gt=0, description="The ID of the group"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get all permissions for a specific group.

    Args:
        group_id: ID of the group
        db: Database session
        current_user: Authenticated user

    Returns:
        List of permissions for the group
    """
    try:
        service = AsyncGroupService(db)
        group = await service.get_group(group_id)
        return group.permissions

    except ResourceNotFoundException as e:
        logger.warning(f"Group not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting group permissions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
