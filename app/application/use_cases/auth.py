# app/application/use_cases/auth.py

from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.adapters.outbound.persistence.models.user_model import User, RefreshToken
from app.adapters.outbound.persistence.models.client_model import Client
from app.adapters.outbound.security.auth_user_manager import UserAuthManager
from app.adapters.outbound.security.auth_client_manager import ClientAuthManager
from app.application.dtos.user_dto import UserCreate, TokenData
from app.domain.exceptions import ResourceNotFoundException, InvalidCredentialsException, ResourceInactiveException

logger = logging.getLogger(__name__)


class AuthService:
    """
    Serviço centralizado para gerenciamento de autenticação.

    Responsável por autenticar usuários e clientes, gerenciar tokens JWT,
    e operações relacionadas à segurança.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com uma sessão de banco de dados."""
        self.db = db

    async def register_user(self, user_data: UserCreate) -> User:
        """
        Registra um novo usuário no sistema.

        Args:
            user_data: Dados do usuário a ser criado

        Returns:
            Usuário criado

        Raises:
            HTTPException: Se o email já estiver em uso ou ocorrer outro erro
        """
        try:
            # Verificar se o usuário já existe
            result = await self.db.execute(select(User).filter(User.email == user_data.email))
            existing_user = result.scalars().first()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email já registrado"
                )

            # Hash da senha
            hashed_password = UserAuthManager.hash_password(user_data.password)

            # Criar o usuário
            new_user = User(
                email=user_data.email,
                password=hashed_password,
                is_active=True,
                is_superuser=False
            )

            # Adicionar ao grupo padrão se necessário
            # Aqui você pode adicionar lógica para associar o usuário
            # ao grupo "user" ou outro grupo padrão

            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)

            return new_user

        except HTTPException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Erro ao registrar usuário: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno ao processar registro: {str(e)}"
            )

    async def authenticate_user(self, email: str, password: str) -> TokenData:
        """
        Autentica um usuário com email e senha.

        Args:
            email: Email do usuário
            password: Senha do usuário

        Returns:
            TokenData contendo tokens de acesso e refresh

        Raises:
            InvalidCredentialsException: Se as credenciais forem inválidas
            ResourceInactiveException: Se o usuário estiver inativo
        """
        try:
            # Buscar o usuário pelo email
            result = await self.db.execute(select(User).filter(User.email == email))
            user = result.scalars().first()

            if not user:
                raise InvalidCredentialsException(detail="Email ou senha incorretos")

            if not user.is_active:
                raise ResourceInactiveException(
                    detail="Conta de usuário inativa",
                    resource_id=user.id
                )

            # Verificar a senha
            if not UserAuthManager.verify_password(password, user.password):
                raise InvalidCredentialsException(detail="Email ou senha incorretos")

            # Gerar tokens
            access_token_expires = timedelta(minutes=120)  # 2 horas
            access_token = UserAuthManager.create_access_token(
                subject=str(user.id),
                expires_delta=access_token_expires
            )

            # Gerar refresh token
            refresh_token_expires = datetime.utcnow() + timedelta(days=7)
            refresh_token_value = UserAuthManager.create_refresh_token(
                subject=str(user.id)
            )

            # Salvar refresh token no banco de dados
            db_refresh_token = RefreshToken(
                token=refresh_token_value,
                user_id=user.id,
                expires_at=refresh_token_expires
            )

            self.db.add(db_refresh_token)
            await self.db.commit()

            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token_value,
                expires_at=datetime.utcnow() + access_token_expires
            )

        except (InvalidCredentialsException, ResourceInactiveException):
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Erro durante autenticação: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno durante autenticação: {str(e)}"
            )

    async def refresh_token(self, refresh_token: str) -> TokenData:
        """
        Gera um novo token de acesso a partir de um refresh token válido.

        Args:
            refresh_token: Token de atualização

        Returns:
            Novo token de acesso

        Raises:
            HTTPException: Se o token for inválido ou expirado
        """
        try:
            # Verificar se o token existe e é válido
            result = await self.db.execute(
                select(RefreshToken).filter(
                    RefreshToken.token == refresh_token,
                    RefreshToken.is_revoked == False,
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )
            token_record = result.scalars().first()

            if not token_record:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token de atualização inválido ou expirado"
                )

            # Buscar o usuário
            result = await self.db.execute(select(User).filter(User.id == token_record.user_id))
            user = result.scalars().first()

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuário não encontrado ou inativo"
                )

            # Gerar novo token de acesso
            access_token_expires = timedelta(minutes=120)
            access_token = UserAuthManager.create_access_token(
                subject=str(user.id),
                expires_delta=access_token_expires
            )

            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token,  # Mantém o mesmo refresh token
                expires_at=datetime.utcnow() + access_token_expires
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Erro ao atualizar token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno ao atualizar token: {str(e)}"
            )

    async def authenticate_client(self, client_id: str, client_secret: str) -> str:
        """
        Autentica um cliente e gera um token JWT.

        Args:
            client_id: ID do cliente
            client_secret: Chave secreta do cliente

        Returns:
            Token JWT de acesso

        Raises:
            InvalidCredentialsException: Se as credenciais forem inválidas
            ResourceInactiveException: Se o cliente estiver inativo
        """
        try:
            # Buscar o cliente pelo ID
            result = await self.db.execute(select(Client).filter(Client.client_id == client_id))
            client = result.scalars().first()

            if not client:
                raise InvalidCredentialsException(detail="Credenciais de cliente inválidas")

            # Verificar status ativo
            if not client.is_active:
                raise ResourceInactiveException(
                    detail="Cliente inativo",
                    resource_id=client.id
                )

            # Verificar a senha
            if not ClientAuthManager.verify_password(client_secret, client.client_secret):
                raise InvalidCredentialsException(detail="Credenciais de cliente inválidas")

            # Gerar token JWT
            token = ClientAuthManager.create_client_token(subject=str(client.id))
            return token

        except (InvalidCredentialsException, ResourceInactiveException):
            raise
        except Exception as e:
            logger.exception(f"Erro ao autenticar cliente: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno ao autenticar cliente: {str(e)}"
            )

    async def revoke_refresh_token(self, token: str) -> bool:
        """
        Revoga um token de atualização.

        Args:
            token: Token de atualização a ser revogado

        Returns:
            True se o token foi revogado com sucesso

        Raises:
            ResourceNotFoundException: Se o token não for encontrado
        """
        try:
            result = await self.db.execute(
                select(RefreshToken).filter(RefreshToken.token == token)
            )
            token_record = result.scalars().first()

            if not token_record:
                raise ResourceNotFoundException(
                    detail="Token não encontrado",
                    resource_id=token
                )

            token_record.is_revoked = True
            await self.db.commit()

            return True

        except ResourceNotFoundException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Erro ao revogar token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno ao revogar token: {str(e)}"
            )

    async def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Revoga todos os tokens de atualização de um usuário.

        Args:
            user_id: ID do usuário

        Returns:
            Número de tokens revogados

        Raises:
            ResourceNotFoundException: Se o usuário não for encontrado
        """
        try:
            # Verificar se o usuário existe
            result = await self.db.execute(select(User).filter(User.id == user_id))
            user = result.scalars().first()

            if not user:
                raise ResourceNotFoundException(
                    detail=f"Usuário com ID {user_id} não encontrado",
                    resource_id=user_id
                )

            # Buscar e revogar todos os tokens do usuário
            result = await self.db.execute(
                select(RefreshToken).filter(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked == False
                )
            )
            tokens = result.scalars().all()

            revoked_count = 0
            for token in tokens:
                token.is_revoked = True
                revoked_count += 1

            await self.db.commit()
            return revoked_count

        except ResourceNotFoundException:
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Erro ao revogar tokens do usuário: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro interno ao revogar tokens: {str(e)}"
            )
