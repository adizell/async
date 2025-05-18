# app/adapters/outbound/persistence/repositories/user_repository.py

"""
Async repository for User entity (user_repository.py).

Handles user operations like create, update, authenticate,
activate/deactivate users with strong validation.
Implements IUserRepository following Clean Architecture principles.
"""

from typing import Optional, List, Dict, Any, Union

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.adapters.outbound.persistence.models import User, AuthGroup
from app.adapters.outbound.persistence.repositories.base_repository import AsyncCRUDBase
from app.application.dtos.user_dto import UserCreate, UserUpdate
from app.application.ports.outbound import IUserRepository
from app.domain.models.user_domain_model import User as DomainUser
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    DatabaseOperationException,
    InvalidCredentialsException,
    ResourceInactiveException,
)
from app.shared.utils.input_validation import InputValidator
from app.adapters.outbound.security.auth_user_manager import UserAuthManager


class AsyncUserCRUD(AsyncCRUDBase[User, UserCreate, UserUpdate], IUserRepository):
    """
    Concrete repository for User entity, fully async.

    Extends AsyncCRUDBase and implements IUserRepository.
    """

    async def get_all_permissions(self, db: AsyncSession, user_id: int) -> set[str]:
        try:
            stmt = select(User).options(
                selectinload(User.permissions),
                selectinload(User.groups).selectinload(AuthGroup.permissions)
            ).where(User.id == user_id)

            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ResourceNotFoundException(message=f"Usuário com ID {user_id} não encontrado.",
                                                resource_id=user_id)

            permissions = {perm.codename for perm in user.permissions}
            for group in user.groups:
                permissions.update(perm.codename for perm in group.permissions)

            return permissions

        except SQLAlchemyError as e:
            self.logger.error(f"Erro ao buscar permissões do usuário: {e}")
            raise DatabaseOperationException("Erro ao buscar permissões do usuário.", original_error=e)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        try:
            result = await db.execute(select(User).where(User.email == email))
            return result.unique().scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error while fetching user by email: {e}")
            raise DatabaseOperationException("Error fetching user by email.", original_error=e)

    async def create_with_password(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        try:
            existing_user = await self.get_by_email(db, obj_in.email)
            if existing_user:
                raise ResourceAlreadyExistsException(detail=f"Email '{obj_in.email}' already exists.")

            is_valid, errors = InputValidator.validate_password(obj_in.password)
            if not is_valid:
                raise InvalidCredentialsException(message="; ".join(errors))

            obj_in_data = jsonable_encoder(obj_in)
            raw_password = obj_in_data.pop("password")

            db_user = User(**obj_in_data)
            db_user.password = await UserAuthManager.hash_password(raw_password)

            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            return db_user

        except (ResourceAlreadyExistsException, InvalidCredentialsException):
            await db.rollback()
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Database error during user creation: {e}")
            raise DatabaseOperationException("Error creating user.", original_error=e)

    async def update_with_password(self, db: AsyncSession, *, db_obj: User,
                                   obj_in: Union[UserUpdate, Dict[str, Any]]) -> User:
        try:
            update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)

            if "email" in update_data and update_data["email"] != db_obj.email:
                existing = await self.get_by_email(db, update_data["email"])
                if existing and existing.id != db_obj.id:
                    raise ResourceAlreadyExistsException(detail=f"Email '{update_data['email']}' is already in use.")

            if "password" in update_data:
                if update_data["password"]:
                    is_valid, errors = InputValidator.validate_password(update_data["password"])
                    if not is_valid:
                        raise InvalidCredentialsException(message="; ".join(errors))
                    update_data["password"] = await UserAuthManager.hash_password(update_data["password"])
                else:
                    del update_data["password"]

            return await super().update(db, db_obj=db_obj, obj_in=update_data)

        except (ResourceAlreadyExistsException, InvalidCredentialsException):
            await db.rollback()
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Database error during user update: {e}")
            raise DatabaseOperationException("Error updating user.", original_error=e)

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> Optional[User]:
        try:
            db_user = await self.get_by_email(db, email)

            if not db_user:
                return None

            if not db_user.is_active:
                raise ResourceInactiveException("Inactive user account.")

            if not await UserAuthManager.verify_password(password, db_user.password):
                return None

            return db_user

        except ResourceInactiveException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during authentication: {e}")
            raise DatabaseOperationException("Error during authentication.", original_error=e)

    async def get_users_with_permissions(self, db: AsyncSession, *, skip: int = 0, limit: int = 100,
                                         include_inactive: bool = False) -> List[User]:
        try:
            query = select(User)
            if not include_inactive:
                query = query.where(User.is_active.is_(true()))

            query = query.options(
                selectinload(User.groups).selectinload(AuthGroup.permissions),
                selectinload(User.permissions)
            ).offset(skip).limit(limit)

            result = await db.execute(query)
            return result.scalars().all()

        except SQLAlchemyError as e:
            self.logger.error(f"Database error while listing users: {e}")
            raise DatabaseOperationException("Error listing users.", original_error=e)

    async def delete(self, db: AsyncSession, *, id: Any) -> None:
        user = await self.get(db, id=id)
        if not user:
            raise ResourceNotFoundException(message=f"User with ID {id} not found.", resource_id=id)

        await db.delete(user)
        await db.commit()

    async def list(self, db: AsyncSession, *, skip: int = 0, limit: int = 100, **filters) -> List[User]:
        return await self.get_multi(db, skip=skip, limit=limit, **filters)

    @staticmethod
    def to_domain(self, db_model: User) -> DomainUser:
        """
        Converte o modelo de persistência para o modelo de domínio.

        Args:
            db_model: Modelo ORM User

        Returns:
            DomainUser: Instância do modelo de domínio
        """
        from app.domain.models.user_domain_model import Group, Permission

        groups = [
            Group(
                id=group_model.id,
                name=group_model.name,
                permissions=[
                    Permission(
                        id=perm.id,
                        name=perm.name,
                        codename=perm.codename,
                        content_type_id=perm.content_type_id,
                    ) for perm in group_model.permissions
                ]
            ) for group_model in db_model.groups
        ]

        permissions = [
            Permission(
                id=perm.id,
                name=perm.name,
                codename=perm.codename,
                content_type_id=perm.content_type_id,
            ) for perm in db_model.permissions
        ]

        return DomainUser(
            id=db_model.id,
            email=db_model.email,
            password=db_model.password,
            is_active=db_model.is_active,
            is_superuser=db_model.is_superuser,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            groups=groups,
            permissions=permissions,
        )

    @staticmethod
    def to_domain_static(db_model: User) -> DomainUser:
        """
        Versão estática de to_domain para compatibilidade com código existente.
        """
        from app.domain.models.user_domain_model import Group, Permission

        groups = [
            Group(
                id=group_model.id,
                name=group_model.name,
                permissions=[
                    Permission(
                        id=perm.id,
                        name=perm.name,
                        codename=perm.codename,
                        content_type_id=perm.content_type_id,
                    ) for perm in group_model.permissions
                ]
            ) for group_model in db_model.groups
        ]

        permissions = [
            Permission(
                id=perm.id,
                name=perm.name,
                codename=perm.codename,
                content_type_id=perm.content_type_id,
            ) for perm in db_model.permissions
        ]

        return DomainUser(
            id=db_model.id,
            email=db_model.email,
            password=db_model.password,
            is_active=db_model.is_active,
            is_superuser=db_model.is_superuser,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            groups=groups,
            permissions=permissions,
        )

    @classmethod
    def from_domain(cls, domain_user: DomainUser) -> User:
        """
        Cria um modelo de persistência a partir do modelo de domínio.

        Args:
            domain_user: Modelo de domínio User

        Returns:
            User: Instância do modelo de persistência
        """
        user = User(
            id=domain_user.id,
            email=domain_user.email,
            password=domain_user.password,
            is_active=domain_user.is_active,
            is_superuser=domain_user.is_superuser,
            created_at=domain_user.created_at,
            updated_at=domain_user.updated_at
        )

        # Nota: As relações (groups, permissions) geralmente são manipuladas separadamente

        return user


# Public instance for use
user_repository = AsyncUserCRUD(User)
