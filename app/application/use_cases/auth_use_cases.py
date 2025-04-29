# app/application/use_cases/auth_use_cases.py (async version)

"""
Service for user authentication.

This module implements the business logic for authentication operations,
including registration, login, and token refresh, following Clean Architecture principles.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.configuration.config import settings
from app.adapters.outbound.security.auth_user_manager import UserAuthManager
from app.adapters.outbound.persistence.models.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_model import User
from app.adapters.outbound.persistence.repositories import user_repository
from app.domain.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    InvalidCredentialsException,
    DatabaseOperationException,
)
from app.application.dtos.user_dto import UserCreate, TokenData

logger = logging.getLogger(__name__)


class AsyncAuthService:
    """
    Service class for user authentication.

    - Handles registration, login, and token refresh operations.
    - Interacts with persistence (repositories) and security modules.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize with a database session.

        Args:
            db_session: Active SQLAlchemy asynchronous session.
        """
        self.db = db_session

    async def register_user(self, user_input: UserCreate) -> User:
        """
        Register a new user.

        Steps:
        1. Ensure the default group 'user' exists.
        2. Hash the user's password securely.
        3. Create the user in the database.
        4. Associate the user with the default group.
        5. Commit transaction and return user.

        Args:
            user_input: Data for the new user.

        Returns:
            User instance.

        Raises:
            ResourceAlreadyExistsException: If the email already exists.
            ResourceNotFoundException: If the default group is missing.
        """
        try:
            # 1. Busca o grupo padrão 'user'
            result = await self.db.execute(
                select(AuthGroup).where(AuthGroup.name == "user")
            )
            group = result.unique().scalar_one_or_none()

            if not group:
                raise ResourceNotFoundException(
                    message="Default group 'user' not found. Cannot register user."
                )

            # 2. Criptografa a senha do usuário
            hashed_password = await UserAuthManager.hash_password(user_input.password)
            user_data = user_input.model_copy(update={"password": hashed_password})

            # 3. Cria o usuário no banco
            user = await user_repository.create(self.db, obj_in=user_data)

            # 4. Associa o usuário ao grupo padrão
            user.groups.append(group)

            # 5. Salva tudo
            await self.db.commit()
            await self.db.refresh(user)

            return user

        except IntegrityError:
            await self.db.rollback()
            raise ResourceAlreadyExistsException(detail="User with provided data already exists.")

    async def login_user(self, user_input: UserCreate) -> TokenData:
        """
        Authenticate a user and generate tokens.

        Args:
            user_input: Login credentials.

        Returns:
            TokenData with access and refresh tokens.

        Raises:
            InvalidCredentialsException: If email or password are invalid.
        """
        # 1. Verifica se o email/senha estão corretos
        user = await user_repository.authenticate(
            self.db,
            email=user_input.email,
            password=user_input.password
        )

        # 2. Gera tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_USER_EXPIRE_MINUTOS)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_id = str(uuid.uuid4())  # Token ID único para rastrear revogações

        access_token = await UserAuthManager.create_access_token(
            subject=str(user.id),
            expires_delta=access_token_expires
        )

        refresh_token = await UserAuthManager.create_refresh_token(
            subject=str(user.id),
            token_id=token_id,
            expires_delta=refresh_token_expires
        )

        expires_at = datetime.now(timezone.utc) + access_token_expires

        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )

    async def refresh_token(self, refresh_token: str) -> TokenData:
        """
        Refresh the authentication tokens.

        Args:
            refresh_token: Valid refresh token.

        Returns:
            New access and refresh tokens.

        Raises:
            InvalidCredentialsException: If refresh token is invalid or user inactive.
            DatabaseOperationException: If any unexpected error occurs.
        """
        try:
            # 1. Valida o refresh token
            payload = await UserAuthManager.verify_refresh_token(refresh_token)

            user_id = payload.get("sub")
            token_id = payload.get("jti")

            if not user_id or not token_id:
                raise InvalidCredentialsException(message="Invalid refresh token.")

            # 2. Confirma se o usuário ainda existe e está ativo
            user = await user_repository.get(self.db, id=user_id)
            if not user or not user.is_active:
                raise InvalidCredentialsException(message="User not found or inactive.")

            # 3. Gera novos tokens
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_USER_EXPIRE_MINUTOS)
            refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

            new_token_id = str(uuid.uuid4())

            new_access_token = await UserAuthManager.create_access_token(
                subject=str(user.id),
                expires_delta=access_token_expires
            )

            new_refresh_token = await UserAuthManager.create_refresh_token(
                subject=str(user.id),
                token_id=new_token_id,
                expires_delta=refresh_token_expires
            )

            expires_at = datetime.now(timezone.utc) + access_token_expires

            return TokenData(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_at=expires_at
            )

        except InvalidCredentialsException:
            raise

        except Exception as e:
            logger.exception(f"Unexpected error during token refresh: {str(e)}")
            raise DatabaseOperationException(
                message="Error processing refresh token.",
                original_error=e
            )
