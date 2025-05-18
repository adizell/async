# app/adapters/inbound/api/v1/endpoints/auth_permission_endpoint.py

"""
API endpoints for permission management.

This module provides endpoints for listing permissions and content types.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi_pagination import Params, Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_permissions_current_user, get_session
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import (
    PermissionOutput,
    ContentTypeOutput
)
from app.application.use_cases.permission_use_cases import AsyncPermissionService
from app.domain.exceptions import (
    ResourceNotFoundException,
    PermissionDeniedException
)
from app.shared.utils.pagination import pagination_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth-permission", tags=["Auth Permission"])


@router.get(
    "",
    response_model=Page[PermissionOutput],
    status_code=status.HTTP_200_OK,
    summary="List Permissions",
    description="List all permissions with pagination. Requires superuser or 'view_permissions' permission."
)
async def list_permissions(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user),
        params: Params = Depends(pagination_params)
):
    """
    List all permissions with pagination.

    Args:
        db: Database session
        current_user: Authenticated user
        params: Pagination parameters

    Returns:
        Paginated list of permissions
    """
    try:
        service = AsyncPermissionService(db)
        return await service.list_permissions(current_user, params)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except Exception as e:
        logger.exception(f"Error listing permissions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/content-types",
    response_model=Page[ContentTypeOutput],
    status_code=status.HTTP_200_OK,
    summary="List Content Types",
    description="List all content types with pagination. Requires superuser or 'view_permissions' permission."
)
async def list_content_types(
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user),
        params: Params = Depends(pagination_params)
):
    """
    List all content types with pagination.

    Args:
        db: Database session
        current_user: Authenticated user
        params: Pagination parameters

    Returns:
        Paginated list of content types
    """
    try:
        service = AsyncPermissionService(db)
        return await service.list_content_types(current_user, params)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except Exception as e:
        logger.exception(f"Error listing content types: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{permission_id}",
    response_model=PermissionOutput,
    status_code=status.HTTP_200_OK,
    summary="Get Permission",
    description="Get a specific permission by ID. Requires superuser or 'view_permissions' permission."
)
async def get_permission(
        permission_id: int = Path(..., gt=0, description="The ID of the permission to get"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get a specific permission by ID.

    Args:
        permission_id: ID of the permission
        db: Database session
        current_user: Authenticated user

    Returns:
        The requested permission
    """
    try:
        service = AsyncPermissionService(db)
        return await service.get_permission(current_user, permission_id)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Permission not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting permission: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/content-types/{content_type_id}",
    response_model=ContentTypeOutput,
    status_code=status.HTTP_200_OK,
    summary="Get Content Type",
    description="Get a specific content type by ID. Requires superuser or 'view_permissions' permission."
)
async def get_content_type(
        content_type_id: int = Path(..., gt=0, description="The ID of the content type to get"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get a specific content type by ID.

    Args:
        content_type_id: ID of the content type
        db: Database session
        current_user: Authenticated user

    Returns:
        The requested content type
    """
    try:
        service = AsyncPermissionService(db)
        return await service.get_content_type(current_user, content_type_id)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Content type not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting content type: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/content-types/{content_type_id}/permissions",
    response_model=List[PermissionOutput],
    status_code=status.HTTP_200_OK,
    summary="Get Content Type Permissions",
    description="Get all permissions for a specific content type. Requires superuser or 'view_permissions' permission."
)
async def get_content_type_permissions(
        content_type_id: int = Path(..., gt=0, description="The ID of the content type"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Get all permissions for a specific content type.

    Args:
        content_type_id: ID of the content type
        db: Database session
        current_user: Authenticated user

    Returns:
        List of permissions for the content type
    """
    try:
        service = AsyncPermissionService(db)
        return await service.get_permissions_by_content_type(current_user, content_type_id)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Content type not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error getting content type permissions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "/{group_id}/permissions",
    response_model=GroupOutput,
    status_code=status.HTTP_200_OK,
    summary="Add Permissions to Group",
    description="Add permissions to a group. Requires superuser or 'manage_groups' permission."
)
async def add_permissions_to_group(
        data: GroupPermissionUpdate,
        group_id: int = Path(..., gt=0, description="The ID of the group"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Add permissions to a group.

    Args:
        data: List of permission IDs to add
        group_id: ID of the group
        db: Database session
        current_user: Authenticated user

    Returns:
        The updated group with permissions

    Example:
        ```
        {
          "permission_ids": [1, 2, 3]
        }
        ```
    """
    try:
        service = AsyncGroupService(db)
        return await service.add_permissions_to_group(current_user, group_id, data)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Group or permissions not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error adding permissions to group: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{group_id}/permissions",
    response_model=GroupOutput,
    status_code=status.HTTP_200_OK,
    summary="Remove Permissions from Group",
    description="Remove permissions from a group. Requires superuser or 'manage_groups' permission."
)
async def remove_permissions_from_group(
        data: GroupPermissionUpdate,
        group_id: int = Path(..., gt=0, description="The ID of the group"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Remove permissions from a group.

    Args:
        data: List of permission IDs to remove
        group_id: ID of the group
        db: Database session
        current_user: Authenticated user

    Returns:
        The updated group with permissions

    Example:
        ```
        {
          "permission_ids": [1, 2, 3]
        }
        ```
    """
    try:
        service = AsyncGroupService(db)
        return await service.remove_permissions_from_group(current_user, group_id, data)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Group not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error removing permissions from group: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
