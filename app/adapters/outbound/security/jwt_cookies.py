# app/adapters/outbound/security/jwt_cookies.py

"""
Gerenciador de JWT com suporte a cookies HTTP.

Este módulo implementa uma classe para criar e verificar tokens JWT
armazenados em cookies HTTP seguros, incluindo proteção CSRF.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
from fastapi import Response, Request
from jose import jwt
import uuid
import secrets
import logging

from app.adapters.configuration.config import settings

# Configurar logger
logger = logging.getLogger(__name__)


class JWTCookieManager:
    """
    Gerenciador de JWT com suporte a cookies seguros.

    Esta classe fornece métodos para:
    - Criar tokens JWT (access e refresh)
    - Definir cookies seguros com esses tokens
    - Verificar tokens JWT de cookies
    - Implementar proteção CSRF para requisições inseguras
    """

    def __init__(self):
        """Inicializa o gerenciador com configurações do settings."""
        # Configurações JWT (das configurações existentes)
        self.secret_key = settings.SECRET_KEY.get_secret_value()
        self.algorithm = settings.ALGORITHM
        self.access_token_expire = timedelta(minutes=settings.ACCESS_TOKEN_USER_EXPIRE_MINUTOS)
        self.refresh_token_expire = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Configurações de cookies (novas configurações)
        self.cookie_domain = getattr(settings, 'COOKIE_DOMAIN', None)
        self.cookie_path = getattr(settings, 'COOKIE_PATH', '/')
        self.cookie_max_age = getattr(settings, 'COOKIE_MAX_AGE', 60 * 60 * 24 * 30)  # 30 dias padrão
        self.cookie_samesite = getattr(settings, 'COOKIE_SAMESITE', 'lax')

        # Configurações CSRF
        self.csrf_protect = getattr(settings, 'CSRF_PROTECT', True)
        self.csrf_header_name = getattr(settings, 'CSRF_HEADER_NAME', 'X-CSRF-Token')

    def create_access_token(
            self,
            subject: str,
            extras: Dict[str, Any] = None,
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Cria um token JWT de acesso.

        Args:
            subject: ID do usuário ou outro identificador único
            extras: Claims adicionais para incluir no token
            expires_delta: Tempo personalizado de expiração (opcional)

        Returns:
            Token JWT codificado como string
        """
        if expires_delta is None:
            expires_delta = self.access_token_expire

        expire = datetime.now(timezone.utc) + expires_delta

        # Payload base do token
        payload = {
            "sub": str(subject),  # Garantir que é string
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "type": "access",
            "jti": str(uuid.uuid4()),  # ID único para este token
        }

        # Adicionar claims extras se fornecidos
        if extras:
            payload.update(extras)

        # Codificar o token
        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )

        return encoded_jwt

    def create_refresh_token(
            self,
            subject: str,
            extras: Dict[str, Any] = None,
            expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Cria um token JWT de refresh.

        Args:
            subject: ID do usuário ou outro identificador único
            extras: Claims adicionais para incluir no token
            expires_delta: Tempo personalizado de expiração (opcional)

        Returns:
            Token JWT de refresh codificado como string
        """
        if expires_delta is None:
            expires_delta = self.refresh_token_expire

        expire = datetime.now(timezone.utc) + expires_delta

        # Payload base do token
        payload = {
            "sub": str(subject),  # Garantir que é string
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "type": "refresh",
            "jti": str(uuid.uuid4()),  # ID único para este token
        }

        # Adicionar claims extras se fornecidos
        if extras:
            payload.update(extras)

        # Codificar o token
        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm
        )

        return encoded_jwt

    def create_csrf_token(self) -> str:
        """
        Cria um token CSRF aleatório.

        Returns:
            String aleatória segura para uso como token CSRF
        """
        return secrets.token_urlsafe(32)

    def set_access_token_cookie(
            self,
            response: Response,
            token: str,
            csrf_token: Optional[str] = None,
            expires_delta: Optional[timedelta] = None
    ):
        """
        Define um cookie com o token de acesso.

        Args:
            response: Objeto Response do FastAPI
            token: Token JWT de acesso
            csrf_token: Token CSRF opcional
            expires_delta: Tempo personalizado de expiração (opcional)
        """
        if expires_delta is None:
            expires_delta = self.access_token_expire

        max_age = int(expires_delta.total_seconds())

        # Cookie principal - HttpOnly para segurança
        response.set_cookie(
            key="access_token",
            value=token,
            max_age=max_age,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=settings.ENVIRONMENT == "production",  # Secure em produção
            httponly=True,  # Protege contra XSS
            samesite=self.cookie_samesite
        )

        # Cookie CSRF (não é HttpOnly para que o JavaScript possa lê-lo)
        if csrf_token and self.csrf_protect:
            response.set_cookie(
                key="csrf_token",
                value=csrf_token,
                max_age=max_age,
                path=self.cookie_path,
                domain=self.cookie_domain,
                secure=settings.ENVIRONMENT == "production",
                httponly=False,  # JavaScript precisa ler para enviar no header
                samesite=self.cookie_samesite
            )

    def set_refresh_token_cookie(
            self,
            response: Response,
            token: str,
            expires_delta: Optional[timedelta] = None
    ):
        """
        Define um cookie com o token de refresh.

        Args:
            response: Objeto Response do FastAPI
            token: Token JWT de refresh
            expires_delta: Tempo personalizado de expiração (opcional)
        """
        if expires_delta is None:
            expires_delta = self.refresh_token_expire

        max_age = int(expires_delta.total_seconds())

        # Cookie de refresh - Restrito ao caminho de refresh
        response.set_cookie(
            key="refresh_token",
            value=token,
            max_age=max_age,
            path="/api/v1/auth/refresh",  # Restrito ao endpoint de refresh
            domain=self.cookie_domain,
            secure=settings.ENVIRONMENT == "production",
            httponly=True,  # Protege contra XSS
            samesite=self.cookie_samesite
        )

    def unset_jwt_cookies(self, response: Response):
        """
        Remove todos os cookies relacionados a JWT.

        Args:
            response: Objeto Response do FastAPI
        """
        # Remove cookie de acesso
        response.delete_cookie(
            key="access_token",
            path=self.cookie_path,
            domain=self.cookie_domain,
        )

        # Remove cookie de refresh
        response.delete_cookie(
            key="refresh_token",
            path="/api/v1/auth/refresh",  # Mesmo caminho usado ao definir
            domain=self.cookie_domain,
        )

        # Remove cookie CSRF
        response.delete_cookie(
            key="csrf_token",
            path=self.cookie_path,
            domain=self.cookie_domain,
        )

    def get_token_from_cookie(
            self,
            request: Request,
            cookie_name: str = "access_token"
    ) -> Optional[str]:
        """
        Extrai um token JWT de um cookie.

        Args:
            request: Objeto Request do FastAPI
            cookie_name: Nome do cookie a obter

        Returns:
            Token JWT ou None se não encontrado
        """
        token = request.cookies.get(cookie_name)
        return token

    def verify_csrf_token(
            self,
            request: Request,
            csrf_cookie: Optional[str] = None
    ) -> bool:
        """
        Verifica se o token CSRF no header corresponde ao cookie.

        Args:
            request: Objeto Request do FastAPI
            csrf_cookie: Valor do cookie CSRF (opcional, extrai do request se não fornecido)

        Returns:
            True se CSRF válido, False caso contrário
        """
        # Se proteção CSRF desativada, sempre retorna True
        if not self.csrf_protect:
            return True

        # Obter token do header
        csrf_header = request.headers.get(self.csrf_header_name)

        # Se não tiver token no header, falha
        if not csrf_header:
            return False

        # Se o cookie não foi fornecido, tenta obtê-lo do request
        if csrf_cookie is None:
            csrf_cookie = request.cookies.get("csrf_token")

        # Se não tiver token no cookie, falha
        if not csrf_cookie:
            return False

        # Compara os tokens
        return csrf_header == csrf_cookie
