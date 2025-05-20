# app/adapters/outbound/security/auth_client_manager.py

import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict

import bcrypt
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.adapters.configuration.config import settings
from app.adapters.outbound.security.jwt_config import JWT_SECRET, JWT_ALGORITHM

# Configure logger
logger = logging.getLogger(__name__)


class ClientAuthManager:
    """
    Authentication Manager for Client operations.

    Responsibilities:
    - Password hashing and verification
    - Client token creation and validation
    """

    crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Client token expiration time
    CLIENT_TOKEN_EXPIRE_DAYS = (
        settings.ACCESS_TOKEN_CLIENT_EXPIRE_DIAS
        if hasattr(settings, "ACCESS_TOKEN_CLIENT_EXPIRE_DIAS")
        else 365
    )

    @classmethod
    async def hash_password(cls, password: str) -> str:
        """Asynchronously hash a password."""
        return cls.crypt_context.hash(password)

    @classmethod
    async def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password."""
        return cls.crypt_context.verify(plain_password, hashed_password)

    @classmethod
    async def create_client_token(
        cls, subject: str, expires_delta: timedelta = None
    ) -> str:
        """Create a client token for authentication."""
        if expires_delta is None:
            expires_delta = timedelta(days=cls.CLIENT_TOKEN_EXPIRE_DAYS)

        expire = datetime.now(timezone.utc) + expires_delta
        jti = str(uuid.uuid4())

        payload = {
            "sub": subject,
            "exp": int(expire.timestamp()),
            "type": "client",
            "jti": jti,
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"Client token created for subject={subject}")
        return token

    @classmethod
    async def verify_client_token(cls, token: str) -> Dict:
        """
        Validate a client token. Raises JWTError if invalid, expired, or type mismatch.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

            if payload.get("type") != "client":
                logger.warning("Client token with incorrect type detected.")
                raise JWTError("Invalid token: incorrect type.")

            return payload

        except JWTError as e:
            logger.warning("Invalid or expired client token: %s", str(e))
            raise
