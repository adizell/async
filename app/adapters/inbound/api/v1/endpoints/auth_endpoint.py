# app/adapters/inbound/api/v1/endpoints/auth_endpoint.py (async version)

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.repositories import token_repository
from app.shared.utils.error_responses import auth_errors
from app.shared.utils.success_responses import auth_success
from app.application.use_cases.auth_use_cases import AsyncAuthService
from app.adapters.inbound.api.deps import get_session, get_current_client
from app.adapters.configuration.config import settings
from app.domain.exceptions import (
    ResourceAlreadyExistsException,
    InvalidCredentialsException,
    ResourceInactiveException,
    ResourceNotFoundException,
)
from app.application.dtos.user_dto import (
    UserCreate,
    UserOutput,
    TokenData,
    RefreshTokenRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Bearer scheme to extract token from Authorization header
bearer_scheme = HTTPBearer()


@router.post(
    "/register",
    response_model=UserOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Register User - Creates a new user",
    description="""
    Creates a new user with email address. A client JWT token is required.

    The password must meet the following criteria:
    - Minimum of 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character (such as !@#$%^&*)
    """,
    responses={**auth_success, **auth_errors}
)
@router.post(
    "/register",
    response_model=UserOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Register User - Creates a new user",
    description="Creates a new user account. Requires a client token.",
    responses={**auth_success, **auth_errors}
)
async def register_user(
        user_input: UserCreate,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_current_client),
):
    try:
        service = AsyncAuthService(db)
        return await service.register_user(user_input)

    except ResourceNotFoundException as e:
        logger.warning(f"Resource not found during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except ResourceAlreadyExistsException as e:
        logger.warning(f"Duplicate registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    except Exception as e:
        logger.exception(f"Unhandled error in registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
    "/login",
    response_model=TokenData,
    summary="Login User - Generates access token",
    description="Authenticates a user and returns a JWT token. Requires a valid client token.",
    responses={**auth_success, **auth_errors},
)
async def login_user(
        user_input: UserCreate,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_current_client),
):
    try:
        service = AsyncAuthService(db)
        return await service.login_user(user_input)

    except InvalidCredentialsException as e:
        logger.warning(f"Invalid credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    except ResourceInactiveException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account. Contact the administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except Exception as e:
        logger.exception(f"Unhandled error in login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
    "/refresh",
    response_model=TokenData,
    summary="Refresh Token - Renews the access token",
    description=(
            "Generates a new access token from a valid refresh token. "
            "Requires a valid client token."
    ),
    responses={**auth_success, **auth_errors}
)
async def refresh_token(
        refresh_data: RefreshTokenRequest,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_current_client),
):
    try:
        service = AsyncAuthService(db)
        return await service.refresh_token(refresh_data.refresh_token)

    except InvalidCredentialsException as e:
        logger.warning(f"Invalid refresh: {e.details}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.details,
            headers={"WWW-Authenticate": "Bearer"},
        )

    except Exception as e:
        logger.exception(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout - Revoke current access token",
    description="Invalidates the current access token by adding it to the blacklist.",
    responses={**auth_success, **auth_errors}
)
async def logout_user(
        credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
        db: AsyncSession = Depends(get_session),
):
    token = credentials.credentials
    try:
        # Decodificar token para obter payload
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token does not support revocation.",
            )

        # Extrair user_id do subject do token
        user_id = payload.get("sub")
        token_type = payload.get("type", "user")

        exp_timestamp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc).replace(tzinfo=None)
        revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Adicionar à blacklist
        await token_repository.add_to_blacklist(
            db,
            jti=jti,
            expires_at=expires_at,
            revoked_at=revoked_at
        )

        return {"detail": "Successfully logged out."}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )
