# app/adapters/inbound/api/v1/endpoints/auth_content_type_endpoint.py

"""
API endpoints for content type management.

This module provides endpoints for creating, reading, updating, and deleting content types,
which are used in the permission system.
"""

import logging
from typing import List

from ecdsa.test_keys import data
from fastapi import APIRouter, Depends, HTTPException, Path, status, Body
from fastapi_pagination import Params, Page
from httpcore import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_permissions_current_user, get_session
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import ContentTypeOutput, PermissionOutput, ContentTypeCreate, ContentTypeUpdate
from app.application.use_cases.content_type_use_cases import AsyncContentTypeService
from app.application.use_cases.permission_use_cases import AsyncPermissionService
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    PermissionDeniedException
)
from app.shared.utils.pagination_utils import pagination_params

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth-content-types", tags=["Auth Content Types"])


@router.get(
    "",
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
        logger.exception(f"Error listing content types: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{content_type_id}",
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
        logger.exception(f"Error getting content type: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get(
    "/{content_type_id}/permissions",
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
        logger.exception(f"Error getting content type permissions: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post(
    "",
    response_model=ContentTypeOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Create Content Type",
    description="Create a new content type. Requires superuser or 'manage_permissions' permission."
)
async def create_content_type(
        data: ContentTypeCreate,  # Precisamos criar este DTO
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Create a new content type.

    Args:
        data: Content type creation data
        db: Database session
        current_user: Authenticated user

    Returns:
        The created content type
    """
    try:
        service = AsyncContentTypeService(db)  # Novo serviço específico para content types
        return await service.create_content_type(current_user, data.app_label, data.model)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceAlreadyExistsException as e:
        logger.warning(f"Content type already exists: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except Exception as e:
        logger.exception(f"Error creating content type: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.put(
    "/{content_type_id}",
    response_model=ContentTypeOutput,
    status_code=status.HTTP_200_OK,
    summary="Update Content Type",
    description="Update a content type. Requires superuser or 'manage_permissions' permission."
)
async def update_content_type(
        # Corrigido: Mudamos a ordem dos parâmetros para evitar o erro de sintaxe
        data: ContentTypeUpdate,  # Precisamos criar este DTO
        content_type_id: int = Path(..., gt=0, description="The ID of the content type to update"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Update a content type.

    Args:
        data: Updated content type data
        content_type_id: ID of the content type
        db: Database session
        current_user: Authenticated user

    Returns:
        The updated content type
    """
    try:
        service = AsyncContentTypeService(db)
        return await service.update_content_type(current_user, content_type_id, data.app_label, data.model)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Content type not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except ResourceAlreadyExistsException as e:
        logger.warning(f"Content type already exists: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    except Exception as e:
        logger.exception(f"Error updating content type: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete(
    "/{content_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Content Type",
    description="Delete a content type. Requires superuser."
)
async def delete_content_type(
        content_type_id: int = Path(..., gt=0, description="The ID of the content type to delete"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user)
):
    """
    Delete a content type.

    Args:
        content_type_id: ID of the content type
        db: Database session
        current_user: Authenticated user
    """
    try:
        service = AsyncContentTypeService(db)
        await service.delete_content_type(current_user, content_type_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning(f"Content type not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.exception(f"Error deleting content type: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
