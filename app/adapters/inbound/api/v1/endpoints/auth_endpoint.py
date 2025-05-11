# app/adapters/inbound/api/v1/endpoints/auth_endpoint.py

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.adapters.inbound.api.deps import get_session, get_permissions_current_client
from app.adapters.outbound.persistence.repositories import token_repository
from app.application.use_cases.auth_use_cases import AsyncAuthService
from app.adapters.outbound.security.jwt_config import JWT_SECRET, JWT_ALGORITHM
from app.application.dtos.user_dto import (
    RefreshTokenRequest,
    UserCreate,
    UserOutput,
    TokenData,
    UserLogin
)
from app.domain.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    InvalidCredentialsException,
    ResourceInactiveException,
    DatabaseOperationException,
)
from app.shared.utils.error_responses import auth_errors
from app.shared.utils.success_responses import auth_success

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}}
)

bearer_scheme = HTTPBearer()


@router.post(
    "/register",
    response_model=UserOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user. Requires a valid client token.",
    responses={**auth_success, **auth_errors}
)
async def register_user(
        user_input: UserCreate,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_permissions_current_client)
):
    service = AsyncAuthService(db)
    try:
        return await service.register_user(user_input)
    except ResourceAlreadyExistsException as e:
        logger.warning(f"Duplicate registration attempt: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ResourceNotFoundException as e:
        logger.warning(f"Default group not found during registration: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error during registration: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.post(
    "/login",
    response_model=TokenData,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticates user credentials and returns a JWT token.",
    responses={**auth_success, **auth_errors}
)
async def login_user(
        user_input: UserLogin,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_permissions_current_client)
):
    service = AsyncAuthService(db)
    try:
        return await service.login_user(user_input)
    except InvalidCredentialsException as e:
        logger.warning(f"Invalid login credentials: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e),
                            headers={"WWW-Authenticate": "Bearer"})
    except ResourceInactiveException as e:
        logger.warning(f"Inactive user trying to login: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e),
                            headers={"WWW-Authenticate": "Bearer"})
    except Exception as e:
        logger.exception(f"Unexpected error during login: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.post(
    "/refresh",
    response_model=TokenData,
    status_code=status.HTTP_200_OK,
    summary="Refresh authentication token",
    description="Generates new access and refresh tokens from a valid refresh token.",
    responses={**auth_success, **auth_errors}
)
async def refresh_token(
        refresh_data: RefreshTokenRequest,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_permissions_current_client)
):
    service = AsyncAuthService(db)
    try:
        return await service.refresh_token(refresh_data.refresh_token)
    except InvalidCredentialsException as e:
        logger.warning(f"Invalid refresh attempt: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e),
                            headers={"WWW-Authenticate": "Bearer"})
    except DatabaseOperationException as e:
        logger.exception(f"Database error during token refresh: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")
    except Exception as e:
        logger.exception(f"Unexpected error during refresh: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Revokes the current access token by blacklisting it.",
    responses={**auth_success, **auth_errors}
)
async def logout_user(
        credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
        db: AsyncSession = Depends(get_session)
):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token does not contain JTI.")

        exp_timestamp = payload.get("exp")
        # expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        expires_at = datetime.utcfromtimestamp(exp_timestamp)
        revoked_at = datetime.utcnow()

        await token_repository.add_to_blacklist(
            db, jti=jti, expires_at=expires_at, revoked_at=revoked_at
        )

        return {"detail": "Successfully logged out."}

    except JWTError as e:
        logger.warning(f"Invalid token during logout: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    except Exception as e:
        logger.exception(f"Unexpected error during logout: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")
