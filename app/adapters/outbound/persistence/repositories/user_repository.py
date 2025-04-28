# app/adapters/outbound/persistence/repositories/user_repository.py (async version)

"""
Repository for user operations.

This module implements the repository that performs database operations
related to users, implementing the IUserRepository interface.
"""

from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from fastapi.encoders import jsonable_encoder
from sqlalchemy import true

from app.adapters.outbound.persistence.repositories.base_repository import AsyncCRUDBase
from app.adapters.outbound.persistence.models import User, AuthGroup
from app.application.dtos.user_dto import UserCreate, UserUpdate
from app.application.ports.outbound import IUserRepository
from app.domain.models.user_domain_model import User as DomainUser
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    DatabaseOperationException,
    InvalidCredentialsException,
)
from app.shared.utils.input_validation import InputValidator


class AsyncUserCRUD(AsyncCRUDBase[User, UserCreate, UserUpdate], IUserRepository):
    """
    Async repository for User entity.

    Provides methods for common user operations like creation with password validation,
    authentication, activation/deactivation, permission loading, and domain conversion.
    Extends a generic async CRUD base.
    """

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        Retrieve a user by email.

        Args:
            db: Database session.
            email: Email to search.

        Returns:
            User object or None.
        """
        try:
            query = select(User).where(User.email == email)
            result = await db.execute(query)
            return result.unique().scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(f"Error fetching user by email '{email}': {e}")
            raise DatabaseOperationException(message="Error fetching user by email", original_error=e)

    async def create_with_password(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """
        Cria um novo usuário com validação e criptografia de senha.
        Garante que senhas sempre sejam criptografadas antes de serem salvas.
        """
        from app.adapters.outbound.security.auth_user_manager import UserAuthManager

        try:
            # Verificar se usuário já existe
            existing_user = await self.get_by_email(db, email=obj_in.email)
            if existing_user:
                self.logger.warning(f"Tentativa de criar usuário com email existente: {obj_in.email}")
                raise ResourceAlreadyExistsException(detail=f"User with email '{obj_in.email}' already exists")

            # Validar senha
            is_valid, errors = InputValidator.validate_password(obj_in.password)
            if not is_valid:
                raise InvalidCredentialsException(message="; ".join(errors))

            # Converter para dicionário e extrair senha
            obj_in_data = jsonable_encoder(obj_in)
            password = obj_in_data.pop("password")

            # Criar objeto e definir senha criptografada
            db_obj = User(**obj_in_data)
            db_obj.password = await UserAuthManager.hash_password(password)

            # Adicionando ao grupo 'user'
            query = select(AuthGroup).where(AuthGroup.name == "user")
            result = await db.execute(query)
            user_group = result.scalar_one_or_none()
            if user_group:
                db_obj.groups.append(user_group)

            # Salvar no banco
            db.add(db_obj)
            await db.commit()
            await db.refresh(db_obj)

            self.logger.info(f"Usuário criado com email: {db_obj.email}")
            return db_obj

        except ResourceAlreadyExistsException:
            await db.rollback()
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Erro ao criar usuário: {e}")
            raise DatabaseOperationException(message="Erro ao criar usuário", original_error=e)

    async def update_with_password(self, db: AsyncSession, *, db_obj: User,
                                   obj_in: Union[UserUpdate, Dict[str, Any]]) -> User:
        """
        Atualiza informações do usuário, incluindo senha se fornecida.

        Garante que senhas sempre sejam criptografadas antes de serem armazenadas.

        Args:
            db: Sessão de banco de dados assíncrona
            db_obj: Objeto de usuário atual no banco de dados
            obj_in: Dados de atualização (esquema Pydantic ou dicionário)

        Returns:
            Usuário atualizado

        Raises:
            ResourceAlreadyExistsException: Se o e-mail já estiver em uso
            InvalidCredentialsException: Se a senha não atender aos requisitos
            DatabaseOperationException: Em caso de erro no banco de dados
        """
        from app.adapters.outbound.security.auth_user_manager import UserAuthManager

        try:
            # Converte para dicionário se for um objeto Pydantic
            update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)

            # Verifica duplicidade de e-mail se estiver sendo alterado
            if "email" in update_data and update_data["email"] != db_obj.email:
                existing = await self.get_by_email(db, email=update_data["email"])
                if existing and existing.id != db_obj.id:
                    raise ResourceAlreadyExistsException(detail=f"Email '{update_data['email']}' já está em uso")

            # PONTO-CHAVE: Tratamento especial para o campo 'password'
            # Verificar e criptografar a senha se presente nos dados de atualização
            if "password" in update_data and update_data["password"]:
                # Validar força da senha
                is_valid, errors = InputValidator.validate_password(update_data["password"])
                if not is_valid:
                    raise InvalidCredentialsException(message="; ".join(errors))

                # Criptografar a senha antes de armazenar
                update_data["password"] = await UserAuthManager.hash_password(update_data["password"])
            elif "password" in update_data and not update_data["password"]:
                # Remover o campo 'password' se estiver vazio para evitar sobrescrever com valor vazio
                del update_data["password"]

            # Atualizar o objeto com os novos valores
            return await super().update(db, db_obj=db_obj, obj_in=update_data)

        except ResourceAlreadyExistsException:
            await db.rollback()
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Erro ao atualizar usuário: {e}")
            raise DatabaseOperationException(message=f"Erro ao atualizar usuário: {str(e)}", original_error=e)

    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        """
        Authenticate user credentials.

        Args:
            db: Database session.
            email: User's email.
            password: Plain password.

        Returns:
            Authenticated User.
        """
        from app.adapters.outbound.security.auth_user_manager import UserAuthManager

        try:
            user = await self.get_by_email(db, email=email)
            if not user:
                self.logger.warning(f"Login attempt with non-existent email: {email}")
                raise InvalidCredentialsException(message="Incorrect email or password")

            if not user.is_active:
                self.logger.warning(f"Login attempt with inactive user: {email}")
                raise InvalidCredentialsException(message="Inactive user")

            if not await UserAuthManager.verify_password(password, user.password):
                self.logger.warning(f"Login attempt with incorrect password: {email}")
                raise InvalidCredentialsException(message="Incorrect email or password")

            return user

        except InvalidCredentialsException:
            raise
        except SQLAlchemyError as e:
            self.logger.error(f"Error authenticating user: {e}")
            raise DatabaseOperationException(message="Error authenticating user", original_error=e)

    async def activate_deactivate(self, db: AsyncSession, *, user_id: UUID, is_active: bool) -> User:
        """
        Activate or deactivate a user.

        Args:
            db: Database session.
            user_id: ID of the user.
            is_active: Desired status.

        Returns:
            Updated user.
        """
        try:
            user = await self.get(db, id=user_id)
            if not user:
                raise ResourceNotFoundException(message=f"User with ID {user_id} not found", resource_id=user_id)

            user.is_active = is_active
            db.add(user)
            await db.commit()
            await db.refresh(user)

            status_text = "activated" if is_active else "deactivated"
            self.logger.info(f"User {user.id} {status_text}")
            return user

        except ResourceNotFoundException:
            await db.rollback()
            raise
        except SQLAlchemyError as e:
            await db.rollback()
            self.logger.error(f"Error changing user status: {str(e)}")
            raise DatabaseOperationException(message=f"Error {'activating' if is_active else 'deactivating'} user",
                                             original_error=e)

    async def get_users_with_permissions(self, db: AsyncSession, *, skip: int = 0, limit: int = 100,
                                         include_inactive: bool = False) -> List[User]:
        """
        List users with their related permissions and groups loaded.

        Args:
            db: Database session.
            skip: Offset for pagination.
            limit: Number of records.
            include_inactive: Include deactivated users.

        Returns:
            List of users.
        """
        try:
            from sqlalchemy.orm import selectinload

            query = select(User)
            if not include_inactive:
                query = query.where(User.is_active.is_(true()))

            query = query.options(
                selectinload(User.groups).selectinload(AuthGroup.permissions),
                selectinload(User.permissions),
            ).offset(skip).limit(limit)

            result = await db.execute(query)
            return result.scalars().all()

        except SQLAlchemyError as e:
            self.logger.error(f"Error listing users with permissions: {str(e)}")
            raise DatabaseOperationException(message="Error listing users with permissions", original_error=e)

    @staticmethod
    def to_domain(db_model: User) -> DomainUser:
        """
        Convert ORM User model into Domain User model.

        Args:
            db_model: SQLAlchemy User model.

        Returns:
            Domain model user.
        """
        from app.domain.models.user_domain_model import Group, Permission

        groups = []
        for group_model in db_model.groups:
            permissions = [
                Permission(
                    id=perm_model.id,
                    name=perm_model.name,
                    codename=perm_model.codename,
                    content_type_id=perm_model.content_type_id,
                ) for perm_model in group_model.permissions
            ]
            groups.append(Group(id=group_model.id, name=group_model.name, permissions=permissions))

        permissions = [
            Permission(
                id=perm_model.id,
                name=perm_model.name,
                codename=perm_model.codename,
                content_type_id=perm_model.content_type_id,
            ) for perm_model in db_model.permissions
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

    async def delete(self, db: AsyncSession, *, id: Any) -> None:
        """
        Delete a user by ID.

        Args:
            db: Database session.
            id: ID of user.

        Raises:
            ResourceNotFoundException: If user not found.
        """
        user = await self.get(db, id=id)
        if not user:
            raise ResourceNotFoundException(message=f"User with ID {id} not found", resource_id=id)

        await db.delete(user)
        await db.commit()

    async def list(self, db: AsyncSession, *, skip: int = 0, limit: int = 100, **filters) -> List[User]:
        """
        List users with optional filtering.

        Args:
            db: Database session.
            skip: Offset for pagination.
            limit: Number of records.
            **filters: Additional filtering parameters.

        Returns:
            List of User objects.
        """
        return await self.get_multi(db, skip=skip, limit=limit, **filters)


# Public instance for use in application
user_repository = AsyncUserCRUD(User)
