# app/application/use_cases/auth_use_cases.py

"""
Service for user authentication.

This module implements the business logic for authentication operations,
following Clean Architecture and Domain-Driven Design principles.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from psycopg2 import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.configuration.config import settings
from app.adapters.outbound.persistence.repositories import user_repository
from app.adapters.outbound.security.auth_user_manager import UserAuthManager
from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.dtos.user_dto import UserCreate, TokenData
from app.domain.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    InvalidCredentialsException,
    DatabaseOperationException,
    ResourceInactiveException,
)

logger = logging.getLogger(__name__)


class AsyncAuthService:
    """
    Application service for authentication-related operations.

    Responsibilities:
    - Register new users
    - Authenticate users and generate JWT tokens
    - Refresh tokens
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize with a database session."""
        self.db = db_session

    async def register_user(self, user_input: UserCreate) -> User:
        """
        Register a new user ensuring group association.

        Raises:
            ResourceAlreadyExistsException: Email already registered.
            ResourceNotFoundException: Default user group not found.
        """
        try:
            result = await self.db.execute(select(AuthGroup).where(AuthGroup.name == "user"))
            group = result.unique().scalar_one_or_none()

            if not group:
                raise ResourceNotFoundException(message="Default group 'user' not found.")

            hashed_password = await UserAuthManager.hash_password(user_input.password)
            user_data = user_input.model_copy(update={"password": hashed_password})

            user = await user_repository.create(self.db, obj_in=user_data)

            user.groups.append(group)
            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"User registered successfully: {user.email}")
            return user

        except IntegrityError:
            await self.db.rollback()
            logger.warning(f"Registration failed - duplicate email: {user_input.email}")
            raise ResourceAlreadyExistsException(detail="User with provided data already exists.")

    async def login_user(self, user_input: UserCreate) -> TokenData:
        """
        Authenticate user and generate access and refresh tokens.

        Raises:
            InvalidCredentialsException: If credentials are incorrect.
            ResourceInactiveException: If user is inactive.
        """
        user = await user_repository.authenticate(
            db=self.db,
            email=user_input.email,
            password=user_input.password
        )

        if not user:
            logger.warning(f"Authentication failed for email: {user_input.email}")
            raise InvalidCredentialsException(message="Incorrect email or password.")

        if not user.is_active:
            logger.warning(f"Inactive user tried to login: {user_input.email}")
            raise ResourceInactiveException(message="Inactive user account.")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_USER_EXPIRE_MINUTOS)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        token_id = str(uuid.uuid4())

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

        logger.info(f"User logged in successfully: {user.email}")

        return TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )

    async def refresh_token(self, refresh_token: str) -> TokenData:
        """
        Validate a refresh token and issue new access and refresh tokens.

        Raises:
            InvalidCredentialsException: If refresh token is invalid or user inactive.
            DatabaseOperationException: For unexpected server/database errors.
        """
        try:
            payload = await UserAuthManager.verify_refresh_token(refresh_token)

            user_id = payload.get("sub")
            token_id = payload.get("jti")

            if not user_id or not token_id:
                logger.warning("Refresh token missing subject or token ID.")
                raise InvalidCredentialsException(message="Invalid refresh token.")

            user = await user_repository.get(self.db, id=user_id)

            if not user or not user.is_active:
                logger.warning(f"User not found or inactive during refresh: {user_id}")
                raise InvalidCredentialsException(message="User not found or inactive.")

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

            logger.info(f"Token refreshed successfully for user: {user.email}")

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
