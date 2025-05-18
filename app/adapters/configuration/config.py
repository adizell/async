# app/adapters/configuration/config.py (async version)

"""
Application Settings Configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# configura corretamente para a raiz do projeto
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path, verbose=True)

from pydantic import SecretStr, AnyHttpUrl, PostgresDsn, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional, List, Union
from logging import getLevelName
from enum import Enum


class Settings(BaseSettings):
    """
    Application Settings for environment configuration, database, auth, logging, and security.
    """
    model_config = ConfigDict(
        env_file=str(env_path),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General Project Info
    PROJECT_NAME: str = Field(default="FastAPI Async Project", description="Name of the project")
    VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, production, testing")
    DEBUG: bool = Field(default=False, description="Enable debug mode (detailed error logs)")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    # Novas configurações para JWT Cookies
    COOKIE_DOMAIN: Optional[str] = Field(default=None, description="Domain for cookies (e.g. example.com)")
    COOKIE_PATH: str = Field(default="/", description="Path for cookies")
    COOKIE_SAMESITE: str = Field(default="lax", description="SameSite policy for cookies: lax, strict, or none")
    COOKIE_MAX_AGE: int = Field(default=60 * 60 * 24 * 30, description="Cookie max age in seconds")

    # Configurações para proteção CSRF
    CSRF_PROTECT: bool = Field(default=True, description="Enable CSRF protection")
    CSRF_HEADER_NAME: str = Field(default="X-CSRF-Token", description="CSRF header name")

    # Controle de visibilidade das rotas na documentação
    SCHEMA_VISIBILITY: bool = False  # True para mostrar todas as rotas, False para ocultar rotas sensíveis

    # Configuração para modo de autenticação
    class AuthMode(str, Enum):
        bearer = "bearer"
        cookie = "cookie"
        hybrid = "hybrid"

    AUTH_MODE: AuthMode = Field(default="bearer", description="Authentication mode: bearer, cookie, or hybrid")

    # Database
    DB_DRIVER: str = Field(default="asyncpg", description="Database driver (asyncpg)")
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: Optional[PostgresDsn] = Field(default=None, description="Database connection URL")
    TEST_MODE: bool = Field(default=False, description="Enable test mode (use test database)")
    TEST_POSTGRES_DB: Optional[str] = Field(default=None, description="Name of the test database")

    # Auth Settings
    SECRET_KEY: SecretStr
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_USER_EXPIRE_MINUTOS: int = Field(default=120, description="Access token expiration time (minutes)")
    ACCESS_TOKEN_CLIENT_EXPIRE_DIAS: int = Field(default=365, description="Client token expiration time (days)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration time (days)")

    # Security (CORS and CSRF)
    BASE_URL: str = Field(default="http://localhost:8000", description="Base URL of the application")
    CORS_ORIGINS: List[AnyHttpUrl] = Field(default=["http://localhost:8000", "http://127.0.0.1:8000"],
                                           description="Allowed CORS origins")
    ALLOWED_ORIGINS: List[AnyHttpUrl] = Field(default=["http://localhost:8000", "http://127.0.0.1:8000"],
                                              description="Allowed Origins for CSRF")
    CSRF_EXEMPT_ROUTES: List[str] = Field(default=["/user/login", "/user/register", "/docs", "/redoc", "/openapi.json"],
                                          description="Routes exempt from CSRF protection")

    # API Documentation
    SCHEMA_VISIBILITY: bool = Field(default=True, description="Show API docs (Swagger UI and Redoc)")

    def model_post_init(self, __context) -> None:
        """Override values with environment variables if they weren't set correctly."""
        # Force load TEST_MODE from environment after model initialization
        env_test_mode = os.getenv("TEST_MODE", "False")
        if env_test_mode.lower() in ("true", "1", "yes", "y", "on"):
            print(f"DEBUG: Overriding TEST_MODE to True (was: {self.TEST_MODE})")
            self.TEST_MODE = True
        else:
            # Respeitar explicitamente o valor False do .env
            print(f"DEBUG: TEST_MODE from env is False, keeping as: {self.TEST_MODE}")

        # Rebuild DATABASE_URL if needed
        if not self.DATABASE_URL:
            # Define se usará o banco de teste SOMENTE se TEST_MODE=True
            # Removendo a lógica automática de usar test para development
            is_test_env = self.TEST_MODE

            # Debug output
            # print(f"DEBUG: TEST_MODE = {self.TEST_MODE}")
            # print(f"DEBUG: ENVIRONMENT = {self.ENVIRONMENT}")
            # print(f"DEBUG: is_test_env = {is_test_env}")
            # print(f"DEBUG: TEST_POSTGRES_DB = {self.TEST_POSTGRES_DB}")
            # print(f"DEBUG: POSTGRES_DB = {self.POSTGRES_DB}")

            if is_test_env and self.TEST_POSTGRES_DB:
                db_name = self.TEST_POSTGRES_DB
                print(f"DEBUG: Using TEST database: {db_name}")
            else:
                db_name = self.POSTGRES_DB
                print(f"DEBUG: Using PRODUCTION database: {db_name}")

            self.DATABASE_URL = PostgresDsn.build(
                scheme=f"postgresql+{self.DB_DRIVER}",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=f"{db_name}",
            )
            print(f"DEBUG: Final DATABASE_URL = {self.DATABASE_URL}")

    @field_validator("TEST_MODE", "DEBUG", "SCHEMA_VISIBILITY", mode="before")
    def parse_boolean(cls, v: Union[str, bool]) -> bool:
        """Convert string boolean values to proper boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "y", "on")
        return bool(v)

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_url(cls, value, info):
        """
        Assemble DATABASE_URL dynamically if not provided directly.
        """
        if value:
            return value

        # Return None to let model_post_init handle it
        return None

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Assemble CORS origins if provided as comma-separated string.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS_ORIGINS format: {v!r}")

    @field_validator("LOG_LEVEL", mode="before")
    def validate_log_level(cls, v: str) -> str:
        """
        Validate that the log level is a valid level name.
        """
        lvl = v.upper()
        if getLevelName(lvl) == "Level %s" % lvl:
            raise ValueError(f"Invalid LOG_LEVEL: {v}")
        return lvl

    # Validação para AUTH_MODE
    @field_validator("AUTH_MODE", mode="before")
    def validate_auth_mode(cls, v: str) -> str:
        """Valida o modo de autenticação."""
        if v.lower() not in ["bearer", "cookie", "hybrid"]:
            raise ValueError(f"AUTH_MODE deve ser 'bearer', 'cookie' ou 'hybrid', recebido: {v}")
        return v.lower()

    # Validação para COOKIE_SAMESITE
    @field_validator("COOKIE_SAMESITE", mode="before")
    def validate_cookie_samesite(cls, v: str) -> str:
        """Valida a política SameSite do cookie."""
        if v.lower() not in ["lax", "strict", "none"]:
            raise ValueError(f"COOKIE_SAMESITE deve ser 'lax', 'strict' ou 'none', recebido: {v}")
        return v.lower()

    # Validação para COOKIE_MAX_AGE
    @field_validator("COOKIE_MAX_AGE", mode="before")
    def validate_cookie_max_age(cls, v: Union[str, int]) -> int:
        """Converte e valida o tempo máximo de vida do cookie."""
        if isinstance(v, str):
            try:
                v = int(v)
            except ValueError:
                raise ValueError(f"COOKIE_MAX_AGE deve ser um número inteiro, recebido: {v}")

        # Certifique-se de que o valor é positivo
        if v <= 0:
            raise ValueError(f"COOKIE_MAX_AGE deve ser positivo, recebido: {v}")
        return v


# Create settings instance
settings = Settings()

# Quick debug if run directly
if __name__ == "__main__":
    import json

    print(json.dumps(settings.model_dump(), indent=4))
