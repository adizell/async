# app/adapters/inbound/api/deps_cookies.py

"""
Dependencies para autenticação com cookies JWT.

Este módulo define injeções de dependência para autenticação
baseada em cookies seguros com JWT tokens.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Request, status, Cookie
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.adapters.outbound.persistence.database import get_db
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.adapters.outbound.persistence.repositories.token_repository import token_repository
from app.adapters.outbound.persistence.repositories.user_repository import user_repository
from app.adapters.outbound.security.jwt_cookies import JWTCookieManager

# Configurar logger
logger = logging.getLogger(__name__)

# Instância global do gerenciador de cookies JWT
jwt_cookie_manager = JWTCookieManager()


async def get_current_user_from_cookie(
        request: Request,
        access_token: Optional[str] = Cookie(None),
        csrf_token: Optional[str] = Cookie(None),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Obtém o usuário atual a partir do token JWT armazenado em cookie.

    Args:
        request: Objeto Request do FastAPI
        access_token: Token JWT do cookie (injetado automaticamente)
        csrf_token: Token CSRF do cookie (injetado automaticamente)
        db: Sessão do banco de dados

    Returns:
        User: Objeto do usuário autenticado

    Raises:
        HTTPException: Se o token for inválido ou o usuário não for encontrado
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication cookie missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar CSRF para métodos não seguros
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        # Extrair CSRF do header
        csrf_header = request.headers.get(jwt_cookie_manager.csrf_header_name)

        # Validar CSRF apenas se estiver ativado nas configurações
        if jwt_cookie_manager.csrf_protect:
            if not csrf_header or not csrf_token or csrf_header != csrf_token:
                logger.warning(f"CSRF validation failed: header={csrf_header}, cookie={csrf_token}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token validation failed",
                )

    try:
        # Decodificar token JWT
        payload = jwt.decode(
            access_token,
            jwt_cookie_manager.secret_key,
            algorithms=[jwt_cookie_manager.algorithm]
        )

        # Verificar tipo de token
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extrair dados de usuário e JTI (token ID)
        user_id = payload.get("sub")
        jti = payload.get("jti")

        # Validar formato e presença de user_id
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verificar se o token está na blacklist
        if jti and await token_repository.is_blacklisted(db, jti):
            logger.warning(f"Attempt to use blacklisted token with JTI: {jti}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Buscar usuário no banco de dados
        user = await user_repository.get(db, id=user_id)

        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"Inactive user tried to authenticate: {user.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user account",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    except JWTError as e:
        logger.warning(f"JWT error during cookie authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during cookie authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Função alternativa que suporta ambos os modos (cookie e bearer)
async def get_current_user_hybrid(
        request: Request,
        access_token: Optional[str] = Cookie(None),
        csrf_token: Optional[str] = Cookie(None),
        authorization: Optional[str] = None,
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Obtém o usuário atual via cookie JWT ou token Bearer.
    Tenta primeiro cookie, depois bearer token.

    Args:
        request: Objeto Request do FastAPI
        access_token: Token JWT do cookie
        csrf_token: Token CSRF do cookie
        authorization: Header de autorização (Bearer token)
        db: Sessão do banco de dados

    Returns:
        User: Objeto do usuário autenticado

    Raises:
        HTTPException: Se todas as autenticações falharem
    """
    # Se tiver cookie, tenta autenticar por cookie
    if access_token:
        try:
            return await get_current_user_from_cookie(request, access_token, csrf_token, db)
        except HTTPException as cookie_error:
            # Se falhar e não tiver Bearer, propaga o erro original
            if not authorization:
                raise cookie_error
            # Se tiver Bearer, tenta esse método (ignora silenciosamente erro de cookie)
            logger.debug("Cookie authentication failed, trying Bearer")

    # Se chegou aqui, não tinha cookie ou falhou. Tenta Bearer.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication method found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extrai token do Bearer
    token = authorization.replace("Bearer ", "")

    try:
        # Restante do código igual ao get_permissions_current_user original
        # Código aqui seria idêntico ao método atual de verificação de token
        # ...

        # Placeholder - isso seria substituído pelo seu código atual
        raise NotImplementedError("Bearer token processing should be implemented using existing logic")

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
