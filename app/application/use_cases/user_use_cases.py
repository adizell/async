# app/application/use_cases/user_use_cases.py (async version)

"""
Service for user management.

This module implements the business logic for user operations,
including registration, authentication, profile updates,
deactivation, reactivation and permanent deletion.

Key design principles
---------------------
* **Asynchronous**: all public methods are async and expect an `AsyncSession`.
* **Single‑responsibility**: each method handles one business capability.
* **Explicit exceptions**: every branch that can fail raises a **domain** exception
  (declared in ``app.domain.exceptions``) – controllers convert those to HTTP errors.
* **Audit‑friendly logging**: important reads/writes are logged with context.
* **Validation first**: user input is validated/sanitised before touching the DB.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate

from app.adapters.outbound.persistence.models import User, AuthGroup
from app.application.dtos.user_dto import UserUpdate, UserSelfUpdate
from app.adapters.outbound.security.auth_user_manager import UserAuthManager
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    InvalidCredentialsException,
    DatabaseOperationException,
    PermissionDeniedException,
    ResourceInactiveException,
)
from app.shared.utils.input_validation import InputValidator

logger = logging.getLogger(__name__)


class AsyncUserService:
    """Service layer (async) for managing **User** entities."""

    def __init__(self, db_session: AsyncSession):
        self.db: AsyncSession = db_session

    # ────────────────────────────────
    # Helpers
    # ────────────────────────────────
    @staticmethod
    def _select_user_stmt(**filters) -> Select:
        """
        Cria uma *query* padrão para `User` carregando coleções via **selectinload**
        (evita `joinedload` + `unique()`) e passando filtros flexíveis.
        """
        return (
            select(User)
            .options(
                selectinload(User.groups),
                selectinload(User.permissions),
            )
            .filter_by(**filters)
        )

    async def _get_user_by_id(self, user_id: UUID) -> User:
        stmt = self._select_user_stmt(id=user_id)
        user = (await self.db.execute(stmt)).scalars().one_or_none()
        if not user:
            logger.warning("User not found: %s", user_id)
            raise ResourceNotFoundException(message="User not found", resource_id=user_id)
        if not user.is_active:
            logger.warning("Inactive user accessed: %s", user_id)
            raise ResourceInactiveException(message="User is inactive", resource_id=user_id)
        return user

    async def _get_user_by_email(self, email: str) -> User:
        stmt = self._select_user_stmt(email=email)
        user = (await self.db.execute(stmt)).scalars().one_or_none()
        if not user:
            logger.warning("User not found by email: %s", email)
            raise ResourceNotFoundException(message="User not found with this email")
        if not user.is_active:
            logger.warning("Inactive user accessed: %s", email)
            raise ResourceInactiveException(message="User is inactive")
        return user

    async def _get_group_by_name(self, name: str) -> AuthGroup:  # pragma: no cover
        result = await self.db.execute(select(AuthGroup).where(AuthGroup.name == name))
        group = result.scalars().one_or_none()  # nenhuma coleção → scalars() direto
        if not group:
            logger.error("Group not found: %s", name)
            raise DatabaseOperationException(message=f"Group '{name}' not found.")
        return group

    # ────────────────────────────────
    # Consultas
    # ────────────────────────────────
    async def list_users(self, current_user: User, params: Params, order: str = "desc"):
        if not current_user.is_superuser:
            logger.warning("Permission denied for listing users: %s", current_user.email)
            raise PermissionDeniedException(message="Only superusers can list users.")
        try:
            query = (
                select(User)
                .options(selectinload(User.groups), selectinload(User.permissions))
                .order_by(User.created_at.desc() if order == "desc" else User.created_at.asc())
            )
            logger.info("Listing users by %s", current_user.email)
            return await paginate(self.db, query, params)
        except Exception as exc:
            logger.exception("Error listing users")
            raise DatabaseOperationException(message="Error listing users", original_error=exc) from exc

    # ────────────────────────────────
    # Self‑service update
    # ────────────────────────────────
    async def update_self(self, user_id: UUID, data: UserSelfUpdate) -> User:
        user = await self._get_user_by_id(user_id)

        # troca de senha
        if data.password:
            if not data.current_password:
                raise InvalidCredentialsException(message="Current password must be provided to change password.")
            if not await UserAuthManager.verify_password(data.current_password, user.password):
                raise InvalidCredentialsException(message="Current password incorrect.")
            is_valid, errors = InputValidator.validate_password(data.password)
            if not is_valid:
                raise InvalidCredentialsException(message="; ".join(errors))
            user.password = await UserAuthManager.hash_password(data.password)

        # troca de e‑mail
        if data.email and data.email != user.email:
            dup_check = select(User.id).where(User.email == data.email, User.id != user_id)
            if (await self.db.execute(dup_check)).scalar_one_or_none():
                raise ResourceAlreadyExistsException(message="Email already in use.")
            user.email = data.email

        await self.db.commit()
        await self.db.refresh(user)
        logger.info("User updated own profile: %s", user.email)
        return user

    # ────────────────────────────────
    # Admin update
    # ────────────────────────────────
    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        stmt = self._select_user_stmt(id=user_id)
        user = (await self.db.execute(stmt)).scalars().one_or_none()
        if not user:
            raise ResourceNotFoundException(message="User not found", resource_id=user_id)

        if data.email and data.email != user.email:
            dup_check = select(User.id).where(User.email == data.email, User.id != user_id)
            if (await self.db.execute(dup_check)).scalar_one_or_none():
                raise ResourceAlreadyExistsException(message="Email already in use.")
            user.email = data.email

        if data.password:
            is_valid, errors = InputValidator.validate_password(data.password)
            if not is_valid:
                raise InvalidCredentialsException(message="; ".join(errors))
            user.password = await UserAuthManager.hash_password(data.password)

        if data.is_active is not None:
            user.is_active = data.is_active
        if data.is_superuser is not None:
            user.is_superuser = data.is_superuser

        await self.db.commit()
        await self.db.refresh(user)
        logger.info("Admin updated user: %s", user.email)
        return user

    # ────────────────────────────────
    # Deactivation / reactivation / deletion
    # ────────────────────────────────
    async def deactivate_user(self, user_id: UUID) -> dict[str, str]:
        user = await self._get_user_by_id(user_id)
        if not user.is_active:
            return {"message": f"User '{user.email}' already inactive."}
        user.is_active = False
        await self.db.commit()
        logger.info("User deactivated: %s", user.email)
        return {"message": f"User '{user.email}' successfully deactivated."}

    async def reactivate_user(self, user_id: UUID) -> dict[str, str]:
        """
        Agora usando a query padrão → evita joinedload + duplicates.
        """
        stmt = self._select_user_stmt(id=user_id)
        user = (await self.db.execute(stmt)).scalars().one_or_none()
        if not user:
            raise ResourceNotFoundException(message="User not found", resource_id=user_id)
        if user.is_active:
            return {"message": f"User '{user.email}' already active."}
        user.is_active = True
        await self.db.commit()
        logger.info("User reactivated: %s", user.email)
        return {"message": f"User '{user.email}' successfully reactivated."}

    async def _get_any_user_by_id(self, user_id: UUID) -> User:
        """
        Return user by id, whether active or inactive.
        Raises ResourceNotFoundException if not found.
        """
        stmt = self._select_user_stmt(id=user_id)
        user = (await self.db.execute(stmt)).scalars().one_or_none()
        if not user:
            logger.warning("User not found: %s", user_id)
            raise ResourceNotFoundException(message="User not found", resource_id=user_id)
        return user

    async def delete_user_permanently(self, user_id: UUID) -> dict[str, str]:
        # user = await self._get_user_by_id(user_id) # Deleta apenas os users ativos
        user = await self._get_any_user_by_id(user_id)  # Deleta users ativos ou inativos
        user.groups.clear()
        user.permissions.clear()
        await self.db.delete(user)
        await self.db.commit()
        logger.info("User permanently deleted: %s", user.email)
        return {"message": f"User '{user.email}' permanently deleted."}
