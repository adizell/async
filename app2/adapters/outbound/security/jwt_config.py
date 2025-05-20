# app/adapters/outbound/security/jwt_config.py

"""Configuração global de JWT para User e Client Authentication."""

import logging
from pydantic import SecretStr
from app.adapters.configuration.config import settings

logger = logging.getLogger(__name__)

# Extrair e normalizar as chaves JWT do settings
_JWT_SECRET: str = (
    settings.SECRET_KEY.get_secret_value()
    if isinstance(settings.SECRET_KEY, SecretStr)
    else settings.SECRET_KEY
)
_JWT_ALGORITHM: str = settings.ALGORITHM


class JWTConfig:
    """Configuração centralizada para JWT."""

    @staticmethod
    def get_secret_key() -> str:
        """Retorna a chave secreta para JWT."""
        return _JWT_SECRET

    @staticmethod
    def get_algorithm() -> str:
        """Retorna o algoritmo para JWT."""
        return _JWT_ALGORITHM


# Exportar para facilitar o uso
JWT_SECRET = JWTConfig.get_secret_key()
JWT_ALGORITHM = JWTConfig.get_algorithm()
