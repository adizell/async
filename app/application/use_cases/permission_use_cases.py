# app/application/use_cases/permission_use_cases.py

"""
Service for permission management.

This module implements the business logic for permission operations,
including listing available permissions and content types.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate

from app.adapters.outbound.persistence.models.user_group.auth_content_type import AuthContentType
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import PermissionOutput
from app.domain.exceptions import (
    PermissionDeniedException,
    ResourceNotFoundException,
    DatabaseOperationException,
    ResourceAlreadyExistsException
)

logger = logging.getLogger(__name__)


class AsyncPermissionService:
    """Service layer for managing permissions and content types."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ────────────────────────────────
    # Helpers
    # ────────────────────────────────
    async def _get_permission_by_id(self, permission_id: int) -> AuthPermission:
        """Get a permission by ID with content type loaded."""
        stmt = (
            select(AuthPermission)
            .options(selectinload(AuthPermission.content_type))
            .where(AuthPermission.id == permission_id)
        )
        permission = (await self.db.execute(stmt)).scalars().one_or_none()

        if not permission:
            logger.warning(f"Permission not found: {permission_id}")
            raise ResourceNotFoundException(message="Permission not found", resource_id=permission_id)

        return permission

    async def _get_content_type_by_id(self, content_type_id: int) -> AuthContentType:
        """Get a content type by ID."""
        stmt = select(AuthContentType).where(AuthContentType.id == content_type_id)
        content_type = (await self.db.execute(stmt)).scalars().one_or_none()

        if not content_type:
            logger.warning(f"Content type not found: {content_type_id}")
            raise ResourceNotFoundException(message="Content type not found", resource_id=content_type_id)

        return content_type

    # ────────────────────────────────
    # Permission Management
    # ────────────────────────────────
    async def list_permissions(self, current_user: User, params: Params) -> Any:
        """
        List all permissions with pagination.

        Args:
            current_user: The authenticated user
            params: Pagination parameters

        Returns:
            Paginated list of permissions

        Raises:
            PermissionDeniedException: If the user doesn't have permission
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} attempted to list permissions without permission")
            raise PermissionDeniedException("You don't have permission to view permissions")

        try:
            stmt = (
                select(AuthPermission)
                .options(selectinload(AuthPermission.content_type))
                .order_by(AuthPermission.codename)
            )

            result = await paginate(self.db, stmt, params)
            return result

        except Exception as e:
            logger.exception(f"Error listing permissions: {str(e)}")
            raise DatabaseOperationException(message="Error listing permissions", original_error=e)

    async def get_permission(self, current_user: User, permission_id: int) -> AuthPermission:
        """
        Get a single permission by ID.

        Args:
            current_user: The authenticated user
            permission_id: ID of the permission to get

        Returns:
            The requested permission

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceNotFoundException: If the permission doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} attempted to view permission details without permission")
            raise PermissionDeniedException("You don't have permission to view permission details")

        return await self._get_permission_by_id(permission_id)

    # ────────────────────────────────
    # Content Type Management
    # ────────────────────────────────
    async def list_content_types(self, current_user: User, params: Params) -> Any:
        """
        List all content types with pagination.

        Args:
            current_user: The authenticated user
            params: Pagination parameters

        Returns:
            Paginated list of content types

        Raises:
            PermissionDeniedException: If the user doesn't have permission
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} attempted to list content types without permission")
            raise PermissionDeniedException("You don't have permission to view content types")

        try:
            stmt = (
                select(AuthContentType)
                .options(selectinload(AuthContentType.permissions))
                .order_by(AuthContentType.app_label, AuthContentType.model)
            )

            result = await paginate(self.db, stmt, params)
            return result

        except Exception as e:
            logger.exception(f"Error listing content types: {str(e)}")
            raise DatabaseOperationException(message="Error listing content types", original_error=e)

    async def get_content_type(self, current_user: User, content_type_id: int) -> AuthContentType:
        """
        Get a single content type by ID.

        Args:
            current_user: The authenticated user
            content_type_id: ID of the content type to get

        Returns:
            The requested content type

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceNotFoundException: If the content type doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} attempted to view content type details without permission")
            raise PermissionDeniedException("You don't have permission to view content type details")

        return await self._get_content_type_by_id(content_type_id)

    async def get_permissions_by_content_type(self, current_user: User, content_type_id: int) -> List[AuthPermission]:
        """
        Get all permissions for a specific content type.

        Args:
            current_user: The authenticated user
            content_type_id: ID of the content type

        Returns:
            List of permissions for the content type

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceNotFoundException: If the content type doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} attempted to view content type permissions without permission")
            raise PermissionDeniedException("You don't have permission to view content type permissions")

        # Check if content type exists
        content_type = await self._get_content_type_by_id(content_type_id)

        try:
            stmt = (
                select(AuthPermission)
                .where(AuthPermission.content_type_id == content_type_id)
                .order_by(AuthPermission.codename)
            )

            permissions = (await self.db.execute(stmt)).scalars().all()
            return permissions

        except Exception as e:
            logger.exception(f"Error getting permissions for content type: {str(e)}")
            raise DatabaseOperationException(
                message="Error getting permissions for content type",
                original_error=e
            )

    # ────────────────────────────────
    # Create Permission
    # ────────────────────────────────
    async def create_permission(
            self, current_user: User, name: str, codename: str, content_type_id: int
    ) -> AuthPermission:
        """
        Cria uma nova permissão.

        Args:
            current_user: O usuário autenticado
            name: Nome da permissão
            codename: Código único da permissão
            content_type_id: ID do tipo de conteúdo associado

        Returns:
            A permissão criada

        Raises:
            PermissionDeniedException: Se o usuário não tiver permissão
            ResourceAlreadyExistsException: Se uma permissão com o mesmo codename já existir
            ResourceNotFoundException: Se o tipo de conteúdo não for encontrado
        """
        # Verificar permissão do usuário
        if not current_user.is_superuser and not current_user.has_permission("manage_permissions"):
            logger.warning(f"User {current_user.email} attempted to create permission without permission")
            raise PermissionDeniedException("You don't have permission to create permissions")

        # Verificar se o codename já existe
        stmt = select(AuthPermission).where(AuthPermission.codename == codename)
        result = await self.db.execute(stmt)
        existing_permission = result.scalars().one_or_none()

        if existing_permission:
            logger.warning(f"Permission with codename '{codename}' already exists")
            raise ResourceAlreadyExistsException(
                detail=f"Permission with codename '{codename}' already exists"
            )

        # Verificar se o tipo de conteúdo existe
        content_type = await self._get_content_type_by_id(content_type_id)

        try:
            # Criar nova permissão
            permission = AuthPermission(
                name=name,
                codename=codename,
                content_type_id=content_type_id
            )

            self.db.add(permission)
            await self.db.commit()
            await self.db.refresh(permission)

            logger.info(f"Permission '{codename}' created by {current_user.email}")
            return permission

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating permission: {str(e)}")
            raise DatabaseOperationException(
                message="Error creating permission",
                original_error=e
            )

    # ────────────────────────────────
    # Delete Permission
    # ────────────────────────────────
    async def delete_permission(self, current_user: User, permission_id: int) -> None:
        """
        Remove uma permissão.

        Args:
            current_user: O usuário autenticado
            permission_id: ID da permissão a ser removida

        Raises:
            PermissionDeniedException: Se o usuário não for superusuário
            ResourceNotFoundException: Se a permissão não for encontrada
        """
        # Apenas superusuários podem excluir permissões
        if not current_user.is_superuser:
            logger.warning(f"User {current_user.email} attempted to delete permission without being a superuser")
            raise PermissionDeniedException("Only superusers can delete permissions")

        # Verificar se a permissão existe
        permission = await self._get_permission_by_id(permission_id)

        try:
            # Remove a permissão
            await self.db.delete(permission)
            await self.db.commit()

            logger.info(f"Permission {permission_id} deleted by {current_user.email}")

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting permission: {str(e)}")
            raise DatabaseOperationException(
                message=f"Error deleting permission",
                original_error=e
            )

    # ────────────────────────────────
    # Search Permissions
    # ────────────────────────────────
    async def search_permissions(self, current_user: User, q: str) -> List[PermissionOutput]:
        """
        Search permissions by name or codename.

        Args:
            current_user: Authenticated user
            q: Search term

        Returns:
            List of permission DTOs

        Raises:
            PermissionDeniedException: If user lacks permission
            DatabaseOperationException: If DB fails
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} tried to search permissions without permission")
            raise PermissionDeniedException("You don't have permission to view permissions")

        try:
            search_term = f"%{q}%"
            stmt = (
                select(AuthPermission)
                .options(selectinload(AuthPermission.content_type))
                .where(
                    or_(
                        AuthPermission.name.ilike(search_term),
                        AuthPermission.codename.ilike(search_term)
                    )
                )
                .order_by(AuthPermission.codename)
            )
            result = await self.db.execute(stmt)
            permissions = result.scalars().all()
            return [PermissionOutput.from_orm(p) for p in permissions]

        except Exception as e:
            logger.exception(f"Error searching permissions: {str(e)}")
            raise DatabaseOperationException("Error searching permissions", original_error=e)
