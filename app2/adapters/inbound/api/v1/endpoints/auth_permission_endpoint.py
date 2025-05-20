# app/adapters/inbound/api/v1/endpoints/auth_permission_endpoint.py

"""
API endpoints for permission management.

This module provides endpoints for listing, retrieving, and managing permissions.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Path, status, Body, Query
from fastapi_pagination import Params, Page
from httpcore import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_permissions_current_user, get_session
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import (
    PermissionOutput,
    ContentTypeOutput, PermissionUpdate, PermissionCreate
)
from app.application.use_cases.permission_use_cases import AsyncPermissionService
from app.domain.exceptions import (
    ResourceNotFoundException,
    PermissionDeniedException,
    ResourceAlreadyExistsException
)
from app.shared.utils.pagination_utils import pagination_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth-permissions", tags=["Auth Permissions"])


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
        logger.exception(f"Error listing permissions: {str(e)}")
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
        logger.exception(f"Error getting permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "",
    response_model=PermissionOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Create Permission",
    description="Create a new permission. Requires superuser or 'manage_permissions' permission."
)
async def create_permission(
        data: PermissionCreate,  # Precisamos criar este DTO
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Create a new permission.

    Args:
        data: Permission creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        The created permission
    """
    try:
        service = AsyncPermissionService(db)
        return await service.create_permission(
            current_user,
            data.name,
            data.codename,
            data.content_type_id
        )

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceAlreadyExistsException as e:
        logger.warning(f"Permission already exists: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Content type not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error creating permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put(
    "/{permission_id}",
    response_model=PermissionOutput,
    status_code=status.HTTP_200_OK,
    summary="Update Permission",
    description="Update a permission. Requires superuser or 'manage_permissions' permission."
)
async def update_permission(
        # Corrigido: Ordem dos parâmetros
        data: PermissionUpdate,  # Precisamos criar este DTO
        permission_id: int = Path(..., gt=0, description="The ID of the permission to update"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Update a permission.

    Args:
        permission_id: ID of the permission
        data: Updated permission data
        db: Database session
        current_user: Authenticated user

    Returns:
        The updated permission
    """
    try:
        service = AsyncPermissionService(db)
        return await service.update_permission(
            current_user,
            permission_id,
            data.name,
            data.codename if "codename" in data.dict() else None,
            data.content_type_id if "content_type_id" in data.dict() else None
        )

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Permission or content type not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except ResourceAlreadyExistsException as e:
        logger.warning(f"Permission already exists: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except Exception as e:
        logger.exception(f"Error updating permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Permission",
    description="Delete a permission. Requires superuser."
)
async def delete_permission(
        permission_id: int = Path(..., gt=0, description="The ID of the permission to delete"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Delete a permission.

    Args:
        permission_id: ID of the permission
        db: Database session
        current_user: Authenticated user
    """
    try:
        service = AsyncPermissionService(db)
        await service.delete_permission(current_user, permission_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Permission not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error deleting permission: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/search",
    response_model=List[PermissionOutput],
    status_code=status.HTTP_200_OK,
    summary="Search Permissions",
    description="Search permissions by name or codename. Requires superuser or 'view_permissions' permission."
)
async def search_permissions(
        q: str = Query(..., min_length=1, description="Search query for name or codename"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Search permissions by name or codename.

    Args:
        q: Search query
        db: Database session
        current_user: Authenticated user

    Returns:
        List of matching permissions
    """
    try:
        service = AsyncPermissionService(db)
        return await service.search_permissions(current_user, q)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except Exception as e:
        logger.exception(f"Error searching permissions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
