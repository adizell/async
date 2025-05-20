# app/adapters/inbound/api/v1/endpoints/user_endpoint.py

from uuid import UUID
from fastapi_pagination import Params, Page
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.application.use_cases.user_use_cases import AsyncUserService
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.domain import ResourceNotFoundException
from app.shared.utils.pagination_utils import pagination_params
from app.adapters.outbound.security.permissions import require_permission_or_superuser
from app.adapters.inbound.api.deps import (
    get_permissions_current_user,
    get_session,
    get_db_session
)
from app.application.dtos.user_dto import (
    UserOutput,
    UserUpdate,
    UserListOutput,
    UserSelfUpdate,
)

router = APIRouter(prefix="/user", tags=["User"])

# Configurar logging
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserOutput)
async def get_my_data(current_user: User = Depends(get_permissions_current_user)):
    if not current_user.is_active:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="This user account is inactive.")
    return current_user


@router.put("/me", response_model=UserOutput)
async def update_my_data(
        update_data: UserSelfUpdate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_permissions_current_user),
):
    service = AsyncUserService(db)
    return await service.update_self(user_id=current_user.id, data=update_data)


@router.get("/list", response_model=Page[UserListOutput])
async def list_users(
        db: AsyncSession = Depends(get_db_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
        params: Params = Depends(pagination_params),
        order: str = Query("desc", enum=["asc", "desc"]),
):
    service = AsyncUserService(db)
    return await service.list_users(current_user=current_user, params=params, order=order)


@router.get("/search/{identifier}", response_model=UserOutput)
async def search_user(
        identifier: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
):
    """
    Busca um usuário específico por email ou ID.

    Args:
        identifier: Email do usuário ou ID (UUID)
        db: Sessão do banco de dados
        current_user: Usuário autenticado (precisa ter permissão list_users)

    Returns:
        Usuário encontrado com suas informações

    Raises:
        404: Se o usuário não for encontrado
        400: Se o identifier for inválido
    """
    service = AsyncUserService(db)

    try:
        # Tenta converter para UUID para verificar se é um ID
        import uuid
        try:
            user_id = uuid.UUID(identifier)
            user = await service._get_user_by_id(user_id)
        except ValueError:
            # Se não for UUID, trata como email
            user = await service._get_user_by_email(identifier)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao buscar usuário: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar usuário")

    return user


# Alternativa: dois endpoints separados para maior clareza

@router.get("/search/email/{email}", response_model=UserOutput)
async def search_user_by_email(
        email: str,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
):
    """
    Busca um usuário específico por email.
    """
    service = AsyncUserService(db)

    try:
        user = await service._get_user_by_email(email)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao buscar usuário por email: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar usuário")

    return user


@router.get("/search/id/{user_id}", response_model=UserOutput)
async def search_user_by_id(
        user_id: UUID,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
):
    """
    Busca um usuário específico por ID.
    """
    service = AsyncUserService(db)

    try:
        user = await service._get_user_by_id(user_id)
    except ResourceNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Erro ao buscar usuário por ID: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro interno ao buscar usuário")

    return user


@router.put("/update/{user_id}", response_model=UserOutput)
async def update_user(
        user_id: UUID,
        update_data: UserUpdate,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
):
    service = AsyncUserService(db)
    return await service.update_user(user_id=user_id, data=update_data)


@router.delete("/deactivate/{user_id}", response_model=dict)
async def deactivate_user(
        user_id: UUID,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
):
    if user_id == current_user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="You cannot deactivate your own user.")

    service = AsyncUserService(db)
    return await service.deactivate_user(user_id=user_id)


@router.post("/reactivate/{user_id}", response_model=dict)
async def reactivate_user(
        user_id: UUID,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
):
    service = AsyncUserService(db)
    return await service.reactivate_user(user_id=user_id)


@router.delete("/delete/{user_id}", response_model=dict)
async def delete_user_permanently(
        user_id: UUID,
        confirm: bool = Query(False),
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(require_permission_or_superuser("list_users")),
):
    from fastapi import HTTPException

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own user.")
    if not confirm:
        raise HTTPException(status_code=400, detail="Permanent deletion requires ?confirm=true")

    service = AsyncUserService(db)
    return await service.delete_user_permanently(user_id=user_id)

# # app/adapters/inbound/api/v1/endpoints/user_endpoint.py
#
# import logging
# from uuid import UUID
# from fastapi_pagination import Params, Page
# from fastapi import APIRouter, Depends, status, Query, HTTPException, Path
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from app.application.use_cases import AsyncAuthService
# from app.shared.utils.error_responses import user_errors
# from app.shared.utils.success_responses import auth_success
# from app.application.use_cases.user_use_cases import AsyncUserService
# from app.adapters.outbound.persistence.models.user_model import User
# from app.shared.utils.pagination import pagination_params
# from app.adapters.outbound.security.permissions import require_superuser, require_permission_or_superuser
# from app.adapters.inbound.api.deps import (
#     get_permissions_current_user,
#     get_session,
#     get_db_session
# )
# from app.domain.exceptions import (
#     ResourceInactiveException,
#     ResourceNotFoundException,
#     InvalidCredentialsException, ResourceAlreadyExistsException
# )
# from app.application.dtos.user_dto import (
#     UserOutput,
#     UserUpdate,
#     UserListOutput,
#     UserSelfUpdate,
#     UserCreate,
# )
#
# logger = logging.getLogger(__name__)
#
# router = APIRouter(
#     prefix="/user",
#     tags=["User"],
# )
#
#
# @router.post("/register", response_model=UserOutput, status_code=status.HTTP_201_CREATED)
# async def register_user(
#         user_input: UserCreate,
#         db: AsyncSession = Depends(get_session),
#         _: str = Depends(get_permissions_current_user),
# ):
#     try:
#         service = AsyncAuthService(db)
#         return await service.register_user(user_input)
#
#     except ResourceAlreadyExistsException as e:
#         msg = getattr(e, "detail", None) or str(e)
#         logger.warning(f"Duplicate registration: {msg}")
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail=msg
#         )
#
#     except HTTPException:
#         raise
#
#     except Exception as e:
#         logger.exception(f"Unhandled error in registration: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error."
#         )
#
#
# @router.get(
#     "/me",
#     response_model=UserOutput,
#     summary="Get My Data - Logged in user data",
#     description="Returns the authenticated user data via JWT token.",
#     responses={**auth_success, **user_errors}
# )
# async def get_my_data(
#         current_user: User = Depends(get_permissions_current_user),
# ):
#     # Additional active status check
#     if not current_user.is_active:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="This user account is inactive.",
#             headers={"WWW-Authenticate": "Bearer"}
#         )
#     return current_user
#
#
# @router.put(
#     "/me",
#     response_model=UserOutput,
#     summary="Update My Data - Update own user data",
#     description="Allows the authenticated user to update their own email and password.",
#     responses={**auth_success, **user_errors}
# )
# async def update_my_data(
#         update_data: UserSelfUpdate,
#         db: AsyncSession = Depends(get_session),
#         current_user: User = Depends(get_permissions_current_user),
# ):
#     """
#     Allows the user to update their own data (email and password).
#     Does not allow the user to change their active/inactive status or permissions.
#     """
#     try:
#         service = AsyncUserService(db)
#         return await service.update_self(user_id=current_user.id, data=update_data)
#
#     except ResourceNotFoundException as e:
#         logger.warning(f"User not found: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=str(e)
#         )
#
#     except InvalidCredentialsException as e:
#         logger.warning(f"Invalid credentials while updating own user: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#
#         )
#
#     except Exception as e:
#         logger.exception(f"Error updating own user: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error."
#         )
#
#
# @router.get(
#     "/list",
#     response_model=Page[UserListOutput],
#     summary="List Users - List all users",
#     description="Returns a paginated list of users. Only superusers have access.",
#     responses={**auth_success, **user_errors}
# )
# async def list_users(
#         db: AsyncSession = Depends(get_db_session),
#         # Access control:
#         # - Superusers: full access
#         # - Users with 'list_users' permission: allowed
#         # current_user: User = Depends(require_superuser) # superuser only
#         # current_user: User = Depends(require_permission("list_users")) # specific permission only
#         current_user: User = Depends(require_permission_or_superuser("list_users")),  # superuser or specific permission
#         params: Params = Depends(pagination_params),  # Usar o pagination_params!
#         order: str = Query("desc", enum=["asc", "desc"], description="Sort by creation date (asc or desc)"),
# ):
#     service = AsyncUserService(db)
#     return await service.list_users(current_user=current_user, params=params, order=order)
#
#
# @router.put(
#     "/update/{user_id}",
#     response_model=UserOutput,
#     summary="Update User - Update a specific user's data",
#     description="Updates a specific user's data. Only superusers have access.",
#     responses={**auth_success, **user_errors}
# )
# async def update_user(
#         user_id: UUID = Path(..., description="ID of the user to update"),
#         update_data: UserUpdate = ...,
#         db: AsyncSession = Depends(get_session),
#         # Access control:
#         # - Superusers: full access
#         # - Users with 'list_users' permission: allowed
#         # current_user: User = Depends(require_superuser) # superuser only
#         # current_user: User = Depends(require_permission("list_users")) # specific permission only
#         current_user: User = Depends(require_permission_or_superuser("list_users")),  # superuser or specific permission
# ):
#     """
#     Allows a superuser to update any user's data.
#     """
#     _ = current_user
#     try:
#         service = AsyncUserService(db)
#         return await service.update_user(user_id=user_id, data=update_data)
#
#     except ResourceNotFoundException as e:
#         logger.exception(f"User not found: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=str(e)
#         )
#
#     except ResourceInactiveException as e:
#         logger.exception(f"The user is inactive: {str(e)} Consider reactivating it through the reactivation endpoint.")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#
#     except InvalidCredentialsException as e:
#         logger.warning(f"Invalid credentials: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail=str(e)
#         )
#
#     except Exception as e:
#         logger.exception(f"Error updating user: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error."
#         )
#
#
# @router.delete(
#     "/deactivate/{user_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Deactivate User - Deactivate a user",
#     description="Deactivates (soft delete) a specific user. Only superusers have access.",
#     response_model=dict,
#     responses={**auth_success, **user_errors}
# )
# async def deactivate_user(
#         user_id: UUID = Path(..., description="ID of the user to deactivate"),
#         db: AsyncSession = Depends(get_session),
#         # Access control:
#         # - Superusers: full access
#         # - Users with 'list_users' permission: allowed
#         # current_user: User = Depends(require_superuser) # superuser only
#         # current_user: User = Depends(require_permission("list_users")) # specific permission only
#         current_user: User = Depends(require_permission_or_superuser("list_users")),  # superuser or specific permission
# ):
#     """
#     Performs soft delete of the user, marking it as inactive.
#     Inactive users cannot log in or access API resources.
#     """
#     if user_id == current_user.id:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="You cannot deactivate your own user."
#         )
#
#     service = AsyncUserService(db)
#     try:
#         return await service.deactivate_user(user_id=user_id)
#
#     except ResourceNotFoundException as e:
#         logger.exception(f"User not found: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=str(e)
#         )
#
#     except Exception as e:
#         logger.exception(f"Unexpected error deactivating user: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error."
#         )
#
#
# @router.post(
#     "/reactivate/{user_id}",
#     status_code=status.HTTP_200_OK,
#     summary="Reactivate User - Reactivate a user",
#     description="Reactivates a previously deactivated user. Only superusers have access.",
#     response_model=dict,
#     responses={**auth_success, **user_errors}
# )
# async def reactivate_user(
#         user_id: UUID = Path(..., description="ID of the user to reactivate"),
#         db: AsyncSession = Depends(get_session),
#         # Access control:
#         # - Superusers: full access
#         # - Users with 'list_users' permission: allowed
#         # current_user: User = Depends(require_superuser) # superuser only
#         # current_user: User = Depends(require_permission("list_users")) # specific permission only
#         current_user: User = Depends(require_permission_or_superuser("list_users")),  # superuser or specific permission
# ):
#     _ = current_user  # Para evitar alerta de "não usado"
#     """
#     Reactivates a user who was inactive, allowing them to log in again.
#     """
#     service = AsyncUserService(db)
#     try:
#         return await service.reactivate_user(user_id=user_id)
#
#     except ResourceNotFoundException as e:
#         logger.exception(f"User not found: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=str(e)
#         )
#
#     except Exception as e:
#         logger.exception(f"Unexpected error reactivating user: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )
#
#
# @router.delete(
#     "/delete/{user_id}",
#     response_model=dict,
#     status_code=status.HTTP_200_OK,
#     summary="Delete User Permanently",
#     description="Permanently deletes a user from the system. Only superusers have access.",
#     responses={**auth_success, **user_errors}
# )
# async def delete_user_permanently(
#         user_id: UUID = Path(..., description="ID of the user to delete"),
#         db: AsyncSession = Depends(get_session),
#         # Access control:
#         # - Superusers: full access
#         # - Users with 'list_users' permission: allowed
#         # current_user: User = Depends(require_superuser) # superuser only
#         # current_user: User = Depends(require_permission("list_users")) # specific permission only
#         current_user: User = Depends(require_permission_or_superuser("list_users")),  # superuser or specific permission
#         confirm: bool = Query(False, description="Explicit confirmation for permanent deletion"),
# ):
#     """
#     Permanently deletes a user from the system.
#     """
#     service = AsyncUserService(db)
#
#     if user_id == current_user.id:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="You cannot delete your own user."
#         )
#
#     if not confirm:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Permanent deletion requires explicit confirmation. Add ?confirm=true to the URL."
#         )
#
#     try:
#         return await service.delete_user_permanently(user_id=user_id)
#
#     except ResourceNotFoundException as e:
#         logger.warning(f"User not found for deletion: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=str(e)
#         )
#
#     except Exception as e:
#         logger.exception(f"Unexpected error deleting user: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Internal server error."
#         )
