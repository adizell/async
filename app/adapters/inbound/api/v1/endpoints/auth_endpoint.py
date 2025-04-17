# app/adapters/inbound/api/v1/endpoints/auth_endpoint.py

import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.use_cases.auth_use_cases import AuthService
from app.adapters.outbound.persistence.models.user_model import User
from app.adapters.inbound.api.deps import (
    get_session,
    get_current_client,
    get_current_user
)
from app.domain.exceptions import (
    ResourceInactiveException,
    ResourceNotFoundException,
    InvalidCredentialsException
)
from app.application.dtos.user_dto import (
    UserCreate,
    UserOutput,
    TokenData,
    RefreshTokenRequest
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Register User - Cria um novo usuário",
    description="Cria um novo usuário com endereço de email. É necessário um token JWT de client para validar a origem da criação.",
)
def register_user(
        user_input: UserCreate,
        db: Session = Depends(get_session),
        _: str = Depends(get_current_client),  # Apenas valida o token do client
):
    try:
        return AuthService(db).register_user(user_input)
    except HTTPException as e:
        # Repassar exceções HTTP
        raise
    except Exception as e:
        logger.exception(f"Erro não tratado no registro: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno no servidor: {str(e)}"
        )


@router.post(
    "/login",
    response_model=TokenData,
    summary="Login User - Gera token de acesso",
    description=(
            "Autentica um usuário (email/senha) e retorna um token JWT. "
            "Tentativas de login com usuários inativos resultarão em erro. "
            "Requer token de client válido."
    ),
)
def login_user(
        user_input: UserCreate,
        db: Session = Depends(get_session),
        _: str = Depends(get_current_client),
):
    try:
        return AuthService(db).login_user(user_input)
    except InvalidCredentialsException as e:
        # Melhora a mensagem para credenciais inválidas
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"}
        )
    except ResourceInactiveException as e:
        # Tratamento específico para usuário inativo
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta de usuário inativa. Por favor, contate o administrador do sistema.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.exception(f"Erro não tratado no login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno no servidor: {str(e)}"
        )


@router.post(
    "/refresh",
    response_model=TokenData,
    summary="Refresh Token - Renova o token de acesso",
    description=(
            "Gera um novo token de acesso a partir de um refresh token válido. "
            "Requer token de client válido."
    ),
)
def refresh_token(
        refresh_data: RefreshTokenRequest,
        db: Session = Depends(get_session),
        _: str = Depends(get_current_client),
):
    try:
        return AuthService(db).refresh_token(refresh_data.refresh_token)
    except InvalidCredentialsException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.detail,
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.exception(f"Erro ao renovar token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao renovar token: {str(e)}"
        )
