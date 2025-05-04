# app/adapters/inbound/api/deps.py (async version)

"""
Dependencies for injection into API endpoints.

This module defines functions that provide dependencies via
FastAPI Depends() for authentication, authorization, and database access.
"""

import logging
from uuid import UUID
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.adapters.outbound.persistence.database import get_db
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.adapters.outbound.persistence.models.user_group.client_model import Client
from app.adapters.outbound.persistence.repositories.token_repository import (
    token_repository,
)
from app.adapters.outbound.persistence.repositories.user_repository import (
    user_repository,
)
from app.adapters.outbound.persistence.repositories.client_repository import (
    client_repository,
)
from app.adapters.outbound.security.auth_client_manager import ClientAuthManager
from app.adapters.outbound.security.jwt_config import JWT_SECRET, JWT_ALGORITHM
from app.adapters.configuration.config import settings

# Configure logger
logger = logging.getLogger(__name__)

# Create bearer scheme for authentication
bearer_scheme = HTTPBearer()


def validate_uuid(uuid_string: str) -> bool:
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False


########################################################################
# Database Session Management
########################################################################

# Aliases for get_db for backward compatibility
get_session = get_db
get_db_session = get_db


########################################################################
# Client Token Authentication
########################################################################


async def verify_client_token(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> str:
    """
    Verify and decode a client JWT token.

    Args:
        credentials: Authorization credentials with bearer token
        db: Database session for blacklist check

    Returns:
        Client ID (sub) contained in the token

    Raises:
        HTTPException: If the token is invalid, expired, or blacklisted
    """
    token = credentials.credentials
    try:
        payload = await ClientAuthManager.verify_client_token(token)

        jti = payload.get("jti")
        if jti and await token_repository.is_blacklisted(db, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        sub = payload.get("sub")
        if not sub:
            logger.warning(f"Invalid client token: 'sub' not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: 'sub' not found in client token.",
            )
        return sub

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_permissions_current_client(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> Client:
    """
    Get the current client from the token.

    Args:
        credentials: Authorization credentials with bearer token
        db: Async database session

    Returns:
        Authenticated Client object

    Raises:
        HTTPException: If the token is invalid or the client doesn't exist/is inactive
    """
    try:
        token = credentials.credentials
        payload = await ClientAuthManager.verify_client_token(token)

        jti = payload.get("jti")
        if jti and await token_repository.is_blacklisted(db, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        client_id = payload.get("sub")
        try:
            client_id = int(client_id)
        except (ValueError, TypeError):
            logger.warning(
                f"Invalid client token: 'sub' is not an integer ({client_id})"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client token: 'sub' is not an integer.",
            )

        client = await client_repository.get(db, id=client_id)

        if not client or not client.is_active:
            logger.warning(f"Client ID {client_id} not found or inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client not found or inactive.",
            )
        return client

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Unexpected error authenticating client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Client authentication error.",
        )


########################################################################
# User Token Authentication
########################################################################


async def get_permissions_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Get the current user from the token.

    Args:
        credentials: Authorization credentials with bearer token
        db: Async database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If the token is invalid or the user doesn't exist/is inactive
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")  # Importante: extrair o JTI (token ID)

        if not user_id or not validate_uuid(user_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verificar se token está na blacklist - ponto crítico
        if jti and await token_repository.is_blacklisted(db, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Buscar o usuário
        user = await user_repository.get(db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
