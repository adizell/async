# app/adapters/inbound/api/v1/endpoints/auth.py

from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.inbound.api.deps import get_db, get_current_client, logger
from app.application.dtos.user_dto import UserCreate, TokenData, TokenRefresh, UserOutput
from app.application.use_cases.auth_use_cases import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserOutput,
    status_code=status.HTTP_201_CREATED,
    summary="Register User - Cria um novo usuário",
    description="Cria um novo usuário com endereço de email. É necessário um token JWT de client para validar a origem da criação.",
)
async def register_user(
        user_input: UserCreate,
        db: AsyncSession = Depends(get_db),
        _: str = Depends(get_current_client),  # Apenas valida o token do client
):
    try:
        auth_service = AuthService(db)
        return await auth_service.register_user(user_input)
    except HTTPException:
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
    summary="Login User - Gera tokens de acesso",
    description="Autentica um usuário (email/senha) e retorna tokens JWT de acesso e refresh. Requer token de client válido.",
)
async def login_user(
        user_input: UserCreate,
        db: AsyncSession = Depends(get_db),
        _: str = Depends(get_current_client),
):
    try:
        auth_service = AuthService(db)
        return await auth_service.login_user(user_input)
    except Exception as e:
        # Error handling logic
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.post(
    "/refresh",
    response_model=TokenData,
    summary="Refresh Token - Renova o token de acesso",
    description="Gera um novo token de acesso usando um refresh token válido.",
)
async def refresh_token(
        refresh_data: TokenRefresh,
        db: AsyncSession = Depends(get_db),
        _: str = Depends(get_current_client),
):
    try:
        auth_service = AuthService(db)
        return await auth_service.refresh_token(refresh_data.refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro ao renovar token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
