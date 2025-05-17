# app/adapters/inbound/api/v1/endpoints/auth_cookie_endpoint.py

"""
Endpoints de autenticação baseada em cookies.

Este módulo fornece endpoints para:
- Login com cookies JWT
- Logout (remoção de cookies)
- Refresh de token via cookies
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.adapters.inbound.api.deps import get_session, get_permissions_current_client
from app.adapters.inbound.api.deps_cookies import jwt_cookie_manager, get_current_user_from_cookie
from app.adapters.outbound.persistence.repositories import token_repository
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.use_cases.auth_use_cases import AsyncAuthService
from app.application.dtos.user_dto import (
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

# Configurar logger
logger = logging.getLogger(__name__)

# Criar router para endpoints com cookies
# IMPORTANTE: Não especificamos o prefixo "/auth-cookie" aqui porque
# este router será incluído em api_router que já tem o prefixo "/api/v1"
router = APIRouter(
    tags=["Authentication with Cookies"],
    responses={404: {"description": "Not found"}}
)


@router.post(
    "/auth-cookie/register",
    response_model=UserOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user. Requires a valid client token."
)
async def register_user(
        user_input: UserCreate,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_permissions_current_client)
):
    """
    Registra um novo usuário.
    Endpoint idêntico ao original mas no namespace /auth-cookie.
    """
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
    "/auth-cookie/login",
    status_code=status.HTTP_200_OK,
    summary="Login user with cookies",
    description="Authenticates user credentials and sets JWT tokens in secure cookies."
)
async def login_with_cookies(
        user_input: UserLogin,
        response: Response,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_permissions_current_client)
):
    """
    Realiza login do usuário e armazena tokens em cookies HTTP seguros.
    Também retorna um token CSRF para uso pelo frontend nos headers.
    """
    service = AsyncAuthService(db)
    try:
        # Usar o serviço existente para login
        token_data = await service.login_user(user_input)

        # Extrair tokens da resposta do serviço
        access_token = token_data.access_token
        refresh_token = token_data.refresh_token

        # Gerar token CSRF aleatório
        csrf_token = jwt_cookie_manager.create_csrf_token()

        # Definir cookies no objeto Response
        jwt_cookie_manager.set_access_token_cookie(response, access_token, csrf_token)
        jwt_cookie_manager.set_refresh_token_cookie(response, refresh_token)

        # Retornar apenas o token CSRF para o cliente.
        # Os tokens JWT ficam apenas nos cookies.
        return {
            "detail": "Login successful",
            # Enviar apenas o token CSRF para o cliente incluir nos headers subsequentes
            "csrf_token": csrf_token,
            # Incluir a data de expiração para o cliente saber quando renovar
            "expires_at": token_data.expires_at
        }

    except InvalidCredentialsException as e:
        logger.warning(f"Invalid login credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except ResourceInactiveException as e:
        logger.warning(f"Inactive user trying to login: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.exception(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
    "/auth-cookie/refresh",
    status_code=status.HTTP_200_OK,
    summary="Refresh authentication cookies",
    description="Generates new access and refresh tokens from a valid refresh token cookie."
)
async def refresh_token_cookie(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_session),
        _: str = Depends(get_permissions_current_client)
):
    """
    Renova tokens usando o refresh_token armazenado em cookie.
    Não requer envio de tokens no corpo, usa diretamente o cookie.
    """
    # Extrair refresh token do cookie
    refresh_token = jwt_cookie_manager.get_token_from_cookie(request, "refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    service = AsyncAuthService(db)
    try:
        # Usar o serviço existente para refresh
        token_data = await service.refresh_token(refresh_token)

        # Extrair novos tokens
        new_access_token = token_data.access_token
        new_refresh_token = token_data.refresh_token

        # Gerar novo token CSRF aleatório
        new_csrf_token = jwt_cookie_manager.create_csrf_token()

        # Definir cookies atualizados
        jwt_cookie_manager.set_access_token_cookie(response, new_access_token, new_csrf_token)
        jwt_cookie_manager.set_refresh_token_cookie(response, new_refresh_token)

        # Retornar apenas o novo token CSRF para o cliente
        return {
            "detail": "Token refreshed successfully",
            "csrf_token": new_csrf_token,
            "expires_at": token_data.expires_at
        }

    except InvalidCredentialsException as e:
        logger.warning(f"Invalid refresh attempt: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.exception(f"Unexpected error during refresh: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.post(
    "/auth-cookie/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user (cookie-based)",
    description="Revokes the current token and removes authentication cookies."
)
async def logout_with_cookies(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_session),
        current_user: User = Depends(get_current_user_from_cookie),
        _: str = Depends(get_permissions_current_client)
):
    """
    Realiza logout do usuário, adicionando o token à blacklist e removendo cookies.
    """
    try:
        # Obter token do cookie para adicionar à blacklist
        token = jwt_cookie_manager.get_token_from_cookie(request, "access_token")

        if token:
            try:
                # Decodificar o token para pegar as informações necessárias
                payload = jwt.decode(
                    token,
                    jwt_cookie_manager.secret_key,
                    algorithms=[jwt_cookie_manager.algorithm]
                )

                # Extrair JTI e data de expiração
                jti = payload.get("jti")
                exp_timestamp = payload.get("exp")

                if jti and exp_timestamp:
                    # Converter timestamp para datetime
                    expires_at = datetime.fromtimestamp(exp_timestamp)
                    revoked_at = datetime.now()

                    # Adicionar à blacklist
                    await token_repository.add_to_blacklist(
                        db,
                        jti=jti,
                        expires_at=expires_at,
                        revoked_at=revoked_at
                    )

                    logger.info(f"Token added to blacklist: {jti}")

            except JWTError as e:
                # Se não conseguir decodificar o token, apenas loga o erro
                # Ainda vamos remover os cookies de qualquer forma
                logger.warning(f"Error decoding token during logout: {e}")

        # Remover todos os cookies de autenticação
        jwt_cookie_manager.unset_jwt_cookies(response)

        return {"detail": "Successfully logged out"}

    except Exception as e:
        logger.exception(f"Unexpected error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error."
        )


@router.get(
    "/auth-cookie/me",
    response_model=UserOutput,
    summary="Get current user profile",
    description="Returns the authenticated user data using cookie authentication."
)
async def get_current_user_cookie(
        current_user: User = Depends(get_current_user_from_cookie),
        _: str = Depends(get_permissions_current_client)
):
    """
    Retorna os dados do usuário atual autenticado via cookie.
    Endpoint equivalente a /user/me mas usando autenticação por cookie.
    """
    return current_user
