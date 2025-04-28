# app/adapters/inbound/api/v1/endpoints/user_endpoint.py (async version)

import logging
from uuid import UUID
from fastapi_pagination import Params, Page
from fastapi import APIRouter, Depends, status, Query, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.utils.error_responses import user_errors
from app.shared.utils.success_responses import auth_success
from app.application.use_cases.user_use_cases import AsyncUserService
from app.adapters.outbound.persistence.models.user_model import User
from app.shared.utils.pagination import pagination_params
from app.adapters.outbound.security.permissions import require_superuser
from app.adapters.inbound.api.deps import (
    get_session,
    get_current_user,
    get_db_session
)
from app.domain.exceptions import (
    ResourceInactiveException,
    ResourceNotFoundException,
    InvalidCredentialsException
)
from app.application.dtos.user_dto import (
    UserOutput,
    UserUpdate,
    UserListOutput,
    UserSelfUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/me",
    response_model=UserOutput,
    summary="Get My Data - Logged in user data",
    description="Returns the authenticated user data via JWT token.",
    responses={**auth_success, **user_errors}
)
async def get_my_data(
        current_user: User = Depends(get_current_user),
):
    # Additional active status check
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This user account is inactive.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user


@router.put(
    "/me",
    response_model=UserOutput,
    summary="Update My Data - Update own user data",
    description="Allows the authenticated user to update their own email and password.",
    responses={**auth_success, **user_errors}
)
async def update_my_data(
        update_data: UserSelfUpdate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user),
):
    """
    Allows the user to update their own data (email and password).
    Does not allow the user to change their active/inactive status or permissions.
    """
    try:
        service = AsyncUserService(db)
        return await service.update_self(user_id=current_user.id, data=update_data)

    except ResourceNotFoundException as e:
        logger.warning(f"User not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except InvalidCredentialsException as e:
        logger.warning(f"Invalid credentials while updating own user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,

        )

    except Exception as e:
        logger.exception(f"Error updating own user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.get(
    "/list",
    response_model=Page[UserListOutput],
    summary="List Users - List all users",
    description="Returns a paginated list of users. Only superusers have access.",
    responses={**auth_success, **user_errors}
)
async def list_users(
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(require_superuser),  # Ensures it's a superuser
        params: Params = Depends(pagination_params),  # Usar O pagination_params!
        order: str = Query("desc", enum=["asc", "desc"], description="Sort by creation date (asc or desc)"),
):
    service = AsyncUserService(db)
    return await service.list_users(current_user=current_user, params=params, order=order)


@router.put(
    "/update/{user_id}",
    response_model=UserOutput,
    summary="Update User - Update a specific user's data",
    description="Updates a specific user's data. Only superusers have access.",
    responses={**auth_success, **user_errors}
)
async def update_user(
        user_id: UUID = Path(..., description="ID of the user to update"),
        update_data: UserUpdate = ...,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_superuser),
):
    """
    Allows a superuser to update any user's data.
    """
    _ = current_user
    try:
        service = AsyncUserService(db)
        return await service.update_user(user_id=user_id, data=update_data)

    except ResourceNotFoundException as e:
        logger.exception(f"User not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except ResourceInactiveException as e:
        logger.exception(f"The user is inactive: {str(e)} Consider reactivating it through the reactivation endpoint.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except InvalidCredentialsException as e:
        logger.warning(f"Invalid credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    except Exception as e:
        logger.exception(f"Error updating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.delete(
    "/deactivate/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate User - Deactivate a user",
    description="Deactivates (soft delete) a specific user. Only superusers have access.",
    response_model=dict,
    responses={**auth_success, **user_errors}
)
async def deactivate_user(
        user_id: UUID = Path(..., description="ID of the user to deactivate"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_superuser),  # Ensures it's a superuser
):
    """
    Performs soft delete of the user, marking it as inactive.
    Inactive users cannot log in or access API resources.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own user."
        )

    service = AsyncUserService(db)
    try:
        return await service.deactivate_user(user_id=user_id)

    except ResourceNotFoundException as e:
        logger.exception(f"User not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.exception(f"Unexpected error deactivating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
    "/reactivate/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Reactivate User - Reactivate a user",
    description="Reactivates a previously deactivated user. Only superusers have access.",
    response_model=dict,
    responses={**auth_success, **user_errors}
)
async def reactivate_user(
        user_id: UUID = Path(..., description="ID of the user to reactivate"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_superuser),  # Ensures it's a superuser
):
    _ = current_user  # Para evitar alerta de "não usado"
    """
    Reactivates a user who was inactive, allowing them to log in again.
    """
    service = AsyncUserService(db)
    try:
        return await service.reactivate_user(user_id=user_id)

    except ResourceNotFoundException as e:
        logger.exception(f"User not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.exception(f"Unexpected error reactivating user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/delete/{user_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Delete User Permanently",
    description="Permanently deletes a user from the system. Only superusers have access.",
    responses={**auth_success, **user_errors}
)
async def delete_user_permanently(
        user_id: UUID = Path(..., description="ID of the user to delete"),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_superuser),
        confirm: bool = Query(False, description="Explicit confirmation for permanent deletion"),
):
    """
    Permanently deletes a user from the system.
    """
    service = AsyncUserService(db)

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user."
        )

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permanent deletion requires explicit confirmation. Add ?confirm=true to the URL."
        )

    try:
        return await service.delete_user_permanently(user_id=user_id)

    except ResourceNotFoundException as e:
        logger.warning(f"User not found for deletion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        logger.exception(f"Unexpected error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )
