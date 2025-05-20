# app/adapters/outbound/security/auth_user_manager.py

import uuid
import logging
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.adapters.configuration.config import settings
from app.adapters.outbound.security.jwt_config import JWT_SECRET, JWT_ALGORITHM
from app.domain.exceptions import InvalidCredentialsException

# Configurar logger
logger = logging.getLogger(__name__)

# Configurações de expiração
_ACCESS_TOKEN_EXPIRE_MINUTES: int = settings.ACCESS_TOKEN_USER_EXPIRE_MINUTOS
_REFRESH_TOKEN_EXPIRE_DAYS: int = settings.REFRESH_TOKEN_EXPIRE_DAYS


class UserAuthManager:
    """
    Authentication Manager for User operations.

    Responsibilities:
    - Password hashing and verification
    - Access and refresh token creation and validation
    """

    crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # ———— PASSWORD METHODS ————

    @classmethod
    async def hash_password(cls, password: str) -> str:
        """Asynchronously hash a password."""
        return cls.crypt_context.hash(password)

    @staticmethod
    def hash_password_sync(password: str) -> str:
        """Synchronously hash a password (for ORM hooks)."""
        password_bytes = password.encode("utf-8")
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode("utf-8")

    @classmethod
    async def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return cls.crypt_context.verify(plain_password, hashed_password)

    # ———— ACCESS TOKEN METHODS ————

    @classmethod
    async def create_access_token(
        cls, subject: str, expires_delta: timedelta = None
    ) -> str:
        """Create an access token for authentication."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)

        expire = datetime.now(timezone.utc) + expires_delta
        jti = str(uuid.uuid4())

        payload = {
            "sub": subject,
            "exp": int(expire.timestamp()),
            "type": "user",
            "jti": jti,
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"Access token created for subject={subject}")
        return token

    @classmethod
    async def verify_access_token(cls, token: str, db: "AsyncSession" = None) -> dict:
        """
        Validate an access token. Raises HTTPException if invalid, expired, or revoked.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "user":
                logger.warning("Access token with incorrect type detected.")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: incorrect type.",
                )

            if db and payload.get("jti"):
                from app.adapters.outbound.persistence.repositories import (
                    token_repository,
                )

                if await token_repository.is_blacklisted(db, payload["jti"]):
                    logger.warning("Revoked token used: jti=%s", payload["jti"])
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token revoked.",
                    )

            return payload

        except JWTError as e:
            logger.warning("Invalid or expired access token: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
            )

    # ———— REFRESH TOKEN METHODS ————

    @classmethod
    async def create_refresh_token(
        cls, subject: str, token_id: str, expires_delta: timedelta = None
    ) -> str:
        """Create a refresh token."""
        if expires_delta is None:
            expires_delta = timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)

        expire = datetime.now(timezone.utc) + expires_delta
        payload = {
            "sub": subject,
            "exp": int(expire.timestamp()),
            "type": "refresh",
            "jti": token_id,
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"Refresh token created for subject={subject}")
        return token

    @classmethod
    async def verify_refresh_token(cls, token: str) -> dict:
        """
        Validate a refresh token. Raises InvalidCredentialsException if invalid or expired.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "refresh":
                logger.warning("Invalid refresh token type: %s", payload.get("type"))
                raise InvalidCredentialsException(message="Invalid refresh token type.")

            return payload

        except JWTError as e:
            logger.warning("Invalid or expired refresh token: %s", str(e))
            raise InvalidCredentialsException(
                message="Invalid or expired refresh token."
            )
