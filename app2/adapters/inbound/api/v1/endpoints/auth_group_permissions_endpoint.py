# app/adapters/inbound/api/v1/endpoints/auth_group_permissions_endpoint.py

"""
API endpoints for group permission management.

This module provides endpoints for managing permissions
associated with groups.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_permissions_current_user, get_session
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import (
    GroupOutput,
    GroupPermissionUpdate
)
from app.application.use_cases.group_use_cases import AsyncGroupService
from app.domain.exceptions import (
    ResourceNotFoundException,
    PermissionDeniedException
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth-groups-permissions", tags=["Auth Group Permissions"])


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
        logger.exception(f"Error adding permissions to group: {str(e)}")
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
        logger.exception(f"Error removing permissions from group: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
