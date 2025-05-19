# app/application/use_cases/user_group_use_cases.py

"""
Service for user-group associations.

This module implements the business logic for managing associations between
users and groups, as well as retrieving user permissions.
"""

import logging
from typing import List, Dict, Any, Set
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.group_dto import (
    UserGroupUpdate,
    UserPermissionOutput
)
from app.domain.exceptions import (
    ResourceNotFoundException,
    PermissionDeniedException,
    DatabaseOperationException
)

logger = logging.getLogger(__name__)


class AsyncUserGroupService:
    """Service layer for managing user-group associations and user permissions."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ────────────────────────────────
    # Helpers
    # ────────────────────────────────
    async def _get_user_by_id(self, user_id: UUID) -> User:
        """Get a user by ID with groups and permissions loaded."""
        stmt = (
            select(User)
            .options(
                selectinload(User.groups).selectinload(AuthGroup.permissions),
                selectinload(User.permissions)
            )
            .where(User.id == user_id)
        )
        user = (await self.db.execute(stmt)).scalars().one_or_none()

        if not user:
            logger.warning(f"User not found: {user_id}")
            raise ResourceNotFoundException(message="User not found", resource_id=user_id)

        return user

    async def _get_groups_by_ids(self, group_ids: List[int]) -> List[AuthGroup]:
        """Get multiple groups by IDs."""
        stmt = select(AuthGroup).where(AuthGroup.id.in_(group_ids))
        result = await self.db.execute(stmt)
        groups = result.scalars().unique().all()  # Adicionando .unique() aqui

        if len(groups) != len(group_ids):
            logger.warning(f"Some group IDs not found: {group_ids}")
            raise ResourceNotFoundException(message="One or more groups not found")

        return groups

    # ────────────────────────────────
    # User-Group Association Management
    # ────────────────────────────────
    async def add_user_to_groups(
            self, current_user: User, user_id: UUID, data: UserGroupUpdate
    ) -> User:
        """
        Add a user to multiple groups.

        Args:
            current_user: The authenticated user
            user_id: ID of the user
            data: List of group IDs to add the user to

        Returns:
            Updated user with groups

        Raises:
            PermissionDeniedException: If the current user doesn't have permission
            ResourceNotFoundException: If the user or groups don't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_user_groups"):
            logger.warning(f"User {current_user.email} attempted to modify user groups without permission")
            raise PermissionDeniedException("You don't have permission to modify user groups")

        # Get target user
        user = await self._get_user_by_id(user_id)

        # Get groups to add
        groups = await self._get_groups_by_ids(data.group_ids)

        try:
            # Add user to groups
            for group in groups:
                if group not in user.groups:
                    user.groups.append(group)

            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"User {user_id} added to groups {data.group_ids} by {current_user.email}")

            # Convert to UserGroupsOutput - Actually, we don't need to do this manually
            # FastAPI will handle the conversion using the from_attributes=True
            return user

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error adding user to groups: {str(e)}")
            raise DatabaseOperationException(message="Error adding user to groups", original_error=e)

    async def get_user_groups(self, current_user: User, user_id: UUID) -> List[AuthGroup]:
        """
        Get all groups a user belongs to.

        Args:
            current_user: The authenticated user
            user_id: ID of the user

        Returns:
            List of groups the user belongs to

        Raises:
            PermissionDeniedException: If the current user doesn't have permission
            ResourceNotFoundException: If the user doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("view_user_groups"):
            # Allow users to see their own groups
            if current_user.id != user_id:
                logger.warning(
                    f"User {current_user.email} attempted to view groups of user {user_id} without permission")
                raise PermissionDeniedException("You don't have permission to view other users' groups")

        # Get user with groups loaded
        user = await self._get_user_by_id(user_id)
        return user.groups

    # ────────────────────────────────
    # User Permission Management
    # ────────────────────────────────
    async def get_user_permissions(self, current_user: User, user_id: UUID) -> UserPermissionOutput:
        """
        Get all permissions a user has (from groups and direct assignments).

        Args:
            current_user: The authenticated user
            user_id: ID of the user

        Returns:
            User permissions output with direct, group, and effective permissions

        Raises:
            PermissionDeniedException: If the current user doesn't have permission
            ResourceNotFoundException: If the user doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("view_user_permissions"):
            # Allow users to see their own permissions
            if current_user.id != user_id:
                logger.warning(
                    f"User {current_user.email} attempted to view permissions of user {user_id} without permission")
                raise PermissionDeniedException("You don't have permission to view other users' permissions")

        # Get user with groups and permissions loaded
        user = await self._get_user_by_id(user_id)

        # Collect all effective permission codenames
        effective_permissions: Set[str] = set()

        # Add direct permissions
        for permission in user.permissions:
            effective_permissions.add(permission.codename)

        # Add permissions from groups
        for group in user.groups:
            for permission in group.permissions:
                effective_permissions.add(permission.codename)

        # If superuser, they have all permissions
        if user.is_superuser:
            effective_permissions.add("*")  # Special indicator for "all permissions"

        # Create the output DTO
        return UserPermissionOutput(
            user_id=str(user.id),
            email=user.email,
            groups=user.groups,
            direct_permissions=user.permissions,
            effective_permissions=sorted(list(effective_permissions))
        )

    async def add_direct_permissions_to_user(
            self, current_user: User, user_id: UUID, permission_ids: List[int]
    ) -> User:
        """
        Add direct permissions to a user.

        Args:
            current_user: The authenticated user
            user_id: ID of the user
            permission_ids: List of permission IDs to add

        Returns:
            Updated user with permissions

        Raises:
            PermissionDeniedException: If the current user doesn't have permission
            ResourceNotFoundException: If the user or permissions don't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_user_permissions"):
            logger.warning(f"User {current_user.email} attempted to modify user permissions without permission")
            raise PermissionDeniedException("You don't have permission to modify user permissions")

        # Get target user
        user = await self._get_user_by_id(user_id)

        try:
            # Get permissions to add
            stmt = select(AuthPermission).where(AuthPermission.id.in_(permission_ids))
            permissions = (await self.db.execute(stmt)).scalars().all()

            if len(permissions) != len(permission_ids):
                logger.warning(f"Some permission IDs not found: {permission_ids}")
                raise ResourceNotFoundException(message="One or more permissions not found")

            # Add permissions to user
            for permission in permissions:
                if permission not in user.permissions:
                    user.permissions.append(permission)

            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"Direct permissions {permission_ids} added to user {user_id} by {current_user.email}")
            return user

        except ResourceNotFoundException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error adding permissions to user: {str(e)}")
            raise DatabaseOperationException(message="Error adding permissions to user", original_error=e)

    async def remove_direct_permissions_from_user(
            self, current_user: User, user_id: UUID, permission_ids: List[int]
    ) -> User:
        """
        Remove direct permissions from a user.

        Args:
            current_user: The authenticated user
            user_id: ID of the user
            permission_ids: List of permission IDs to remove

        Returns:
            Updated user with permissions

        Raises:
            PermissionDeniedException: If the current user doesn't have permission
            ResourceNotFoundException: If the user doesn't exist
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_user_permissions"):
            logger.warning(f"User {current_user.email} attempted to modify user permissions without permission")
            raise PermissionDeniedException("You don't have permission to modify user permissions")

        # Get target user
        user = await self._get_user_by_id(user_id)

        try:
            # Get permissions to remove
            stmt = select(AuthPermission).where(AuthPermission.id.in_(permission_ids))
            permissions_to_remove = (await self.db.execute(stmt)).scalars().all()

            # Remove permissions from user
            for permission in permissions_to_remove:
                if permission in user.permissions:
                    user.permissions.remove(permission)

            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"Direct permissions {permission_ids} removed from user {user_id} by {current_user.email}")
            return user

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error removing permissions from user: {str(e)}")
            raise DatabaseOperationException(message="Error removing permissions from user", original_error=e)

    async def set_user_superuser_status(
            self, current_user: User, user_id: UUID, is_superuser: bool
    ) -> User:
        """
        Set a user's superuser status.

        Args:
            current_user: The authenticated user
            user_id: ID of the user
            is_superuser: New superuser status

        Returns:
            Updated user

        Raises:
            PermissionDeniedException: If the current user isn't a superuser
            ResourceNotFoundException: If the user doesn't exist
        """
        # Only superusers can promote/demote superusers
        if not current_user.is_superuser:
            logger.warning(f"User {current_user.email} attempted to change superuser status without being a superuser")
            raise PermissionDeniedException("Only superusers can change superuser status")

        # Get target user
        user = await self._get_user_by_id(user_id)

        try:
            # Update superuser status
            user.is_superuser = is_superuser
            await self.db.commit()
            await self.db.refresh(user)

            action = "promoted to" if is_superuser else "demoted from"
            logger.info(f"User {user_id} {action} superuser by {current_user.email}")
            return user

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating superuser status: {str(e)}")
            raise DatabaseOperationException(message="Error updating superuser status", original_error=e)
