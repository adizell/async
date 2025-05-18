# app/application/use_cases/group_use_cases.py

"""
Service for group management.

This module implements the business logic for group operations,
including creation, listing, updating, and deletion of groups,
as well as managing group permissions.
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate

from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import (
    GroupCreate,
    GroupUpdate,
    GroupOutput,
    GroupPermissionUpdate
)
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    PermissionDeniedException,
    DatabaseOperationException
)

logger = logging.getLogger(__name__)


class AsyncGroupService:
    """Service layer for managing groups and group permissions."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ────────────────────────────────
    # Helpers
    # ────────────────────────────────
    async def _get_group_by_id(self, group_id: int) -> AuthGroup:
        """Get a group by ID with permissions loaded."""
        stmt = (
            select(AuthGroup)
            .options(selectinload(AuthGroup.permissions))
            .where(AuthGroup.id == group_id)
        )
        group = (await self.db.execute(stmt)).scalars().one_or_none()

        if not group:
            logger.warning(f"Group not found: {group_id}")
            raise ResourceNotFoundException(message="Group not found", resource_id=group_id)

        return group

    async def _check_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Check if a group with the given name already exists."""
        stmt = select(AuthGroup.id).where(AuthGroup.name == name)

        if exclude_id is not None:
            stmt = stmt.where(AuthGroup.id != exclude_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ────────────────────────────────
    # Group Management
    # ────────────────────────────────
    async def create_group(self, current_user: User, data: GroupCreate) -> GroupOutput:
        """
        Create a new permission group.

        Args:
            current_user: The authenticated user creating the group
            data: Group creation data

        Returns:
            The created group

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceAlreadyExistsException: If a group with the name already exists
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_groups"):
            logger.warning(f"User {current_user.email} attempted to create a group without permission")
            raise PermissionDeniedException("You don't have permission to create groups")

        # Check if name already exists
        if await self._check_name_exists(data.name):
            logger.warning(f"Group with name '{data.name}' already exists")
            raise ResourceAlreadyExistsException(detail=f"Group with name '{data.name}' already exists")

        # Create new group
        try:
            group = AuthGroup(name=data.name)
            self.db.add(group)
            await self.db.commit()
            await self.db.refresh(group)

            logger.info(f"Group '{data.name}' created by {current_user.email}")
            return group

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating group: {str(e)}")
            raise DatabaseOperationException(message="Error creating group", original_error=e)

    async def list_groups(self, current_user: User, params: Params) -> Any:
        """
        List all groups with pagination.

        Args:
            current_user: The authenticated user
            params: Pagination parameters

        Returns:
            Paginated list of groups
        """
        try:
            stmt = (
                select(AuthGroup)
                .options(selectinload(AuthGroup.permissions))
                .order_by(AuthGroup.name)
            )

            result = await paginate(self.db, stmt, params)
            return result

        except Exception as e:
            logger.exception(f"Error listing groups: {str(e)}")
            raise DatabaseOperationException(message="Error listing groups", original_error=e)

    async def get_group(self, group_id: int) -> AuthGroup:
        """
        Get a single group by ID.

        Args:
            group_id: ID of the group to get

        Returns:
            The requested group

        Raises:
            ResourceNotFoundException: If the group doesn't exist
        """
        return await self._get_group_by_id(group_id)

    async def update_group(self, current_user: User, group_id: int, data: GroupUpdate) -> AuthGroup:
        """
        Update a group's information.

        Args:
            current_user: The authenticated user
            group_id: ID of the group to update
            data: Updated group data

        Returns:
            The updated group

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceNotFoundException: If the group doesn't exist
            ResourceAlreadyExistsException: If the new name already exists
        """
        # Verificar permissão
        if not current_user.is_superuser and not current_user.has_permission("manage_groups"):
            logger.warning(f"User {current_user.email} attempted to update a group without permission")
            raise PermissionDeniedException("You don't have permission to update groups")

        # Obter grupo existente
        group = await self._get_group_by_id(group_id)

        # Atualizar atributos (apenas se fornecidos)
        if data.name and data.name != group.name:
            # Verificar duplicação de nome
            if await self._check_name_exists(data.name, exclude_id=group_id):
                logger.warning(f"Group with name '{data.name}' already exists")
                raise ResourceAlreadyExistsException(detail=f"Group with name '{data.name}' already exists")

            # Atualizar nome no objeto existente
            group.name = data.name

        try:
            # Persistir alterações
            self.db.add(group)
            await self.db.commit()
            await self.db.refresh(group)

            logger.info(f"Group {group_id} updated by {current_user.email}")
            return group

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating group: {str(e)}")
            raise DatabaseOperationException(message="Error updating group", original_error=e)

    async def delete_group(self, current_user: User, group_id: int) -> Dict[str, str]:
        """
        Delete a group.

        Args:
            current_user: The authenticated user
            group_id: ID of the group to delete

        Returns:
            Success message

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceNotFoundException: If the group doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_groups"):
            logger.warning(f"User {current_user.email} attempted to delete a group without permission")
            raise PermissionDeniedException("You don't have permission to delete groups")

        # Get existing group
        group = await self._get_group_by_id(group_id)

        # Check if it's a system group
        if group.name in ["admin", "user", "owner", "visitor"]:
            logger.warning(f"User {current_user.email} attempted to delete system group '{group.name}'")
            raise PermissionDeniedException(f"Cannot delete system group '{group.name}'")

        try:
            # Remove associations with users and permissions
            group.permissions.clear()

            # Delete the group
            await self.db.delete(group)
            await self.db.commit()

            logger.info(f"Group {group_id} ('{group.name}') deleted by {current_user.email}")
            return {"message": f"Group '{group.name}' successfully deleted"}

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting group: {str(e)}")
            raise DatabaseOperationException(message="Error deleting group", original_error=e)

    # ────────────────────────────────
    # Group Permission Management
    # ────────────────────────────────
    async def add_permissions_to_group(
            self, current_user: User, group_id: int, data: GroupPermissionUpdate
    ) -> AuthGroup:
        """
        Add permissions to a group.

        Args:
            current_user: The authenticated user
            group_id: ID of the group
            data: List of permission IDs to add

        Returns:
            Updated group with permissions

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceNotFoundException: If the group or permissions don't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_groups"):
            logger.warning(f"User {current_user.email} attempted to modify group permissions without permission")
            raise PermissionDeniedException("You don't have permission to modify group permissions")

        # Get existing group
        group = await self._get_group_by_id(group_id)

        # Get permissions to add
        stmt = select(AuthPermission).where(AuthPermission.id.in_(data.permission_ids))
        permissions = (await self.db.execute(stmt)).scalars().all()

        if len(permissions) != len(data.permission_ids):
            logger.warning(f"Some permission IDs not found: {data.permission_ids}")
            raise ResourceNotFoundException(message="One or more permissions not found")

        try:
            # Add permissions to group
            for permission in permissions:
                if permission not in group.permissions:
                    group.permissions.append(permission)

            await self.db.commit()
            await self.db.refresh(group)

            logger.info(f"Permissions {data.permission_ids} added to group {group_id} by {current_user.email}")
            return group

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error adding permissions to group: {str(e)}")
            raise DatabaseOperationException(
                message="Error adding permissions to group",
                original_error=e
            )

    async def remove_permissions_from_group(
            self, current_user: User, group_id: int, data: GroupPermissionUpdate
    ) -> AuthGroup:
        """
        Remove permissions from a group.

        Args:
            current_user: The authenticated user
            group_id: ID of the group
            data: List of permission IDs to remove

        Returns:
            Updated group with permissions

        Raises:
            PermissionDeniedException: If the user doesn't have permission
            ResourceNotFoundException: If the group doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_groups"):
            logger.warning(f"User {current_user.email} attempted to modify group permissions without permission")
            raise PermissionDeniedException("You don't have permission to modify group permissions")

        # Get existing group
        group = await self._get_group_by_id(group_id)

        try:
            # Get permissions to remove
            stmt = select(AuthPermission).where(AuthPermission.id.in_(data.permission_ids))
            permissions = (await self.db.execute(stmt)).scalars().all()

            # Remove permissions from group
            for permission in permissions:
                if permission in group.permissions:
                    group.permissions.remove(permission)

            await self.db.commit()
            await self.db.refresh(group)

            logger.info(f"Permissions {data.permission_ids} removed from group {group_id} by {current_user.email}")
            return group

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error removing permissions from group: {str(e)}")
            raise DatabaseOperationException(
                message="Error removing permissions from group",
                original_error=e
            )
