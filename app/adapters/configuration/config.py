# app/adapters/configuration/config.py (async version)

"""
Application Settings Configuration
"""

from typing import Optional, List, Union
from logging import getLevelName
from pydantic import PostgresDsn, Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application Settings for environment configuration, database, auth, logging, and security.
    """

    # General Project Info
    PROJECT_NAME: str = Field(default="FastAPI Async Project", description="Name of the project")
    VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, production, testing")
    DEBUG: bool = Field(default=False, description="Enable debug mode (detailed error logs)")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

    # Database
    DB_DRIVER: str = Field(default="asyncpg", description="Database driver (asyncpg)")
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    DATABASE_URL: Optional[PostgresDsn] = None
    TEST_MODE: bool = Field(default=False, description="Enable test mode (use test database)")
    TEST_POSTGRES_DB: Optional[str] = Field(default=None, description="Name of the test database")

    # Auth Settings
    SECRET_KEY: str
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_USER_EXPIRE_MINUTOS: int = Field(default=120, description="Access token expiration time (minutes)")
    ACCESS_TOKEN_CLIENT_EXPIRE_DIAS: int = Field(default=365, description="Client token expiration time (days)")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration time (days)")

    # Security (CORS and CSRF)
    BASE_URL: str = Field(default="http://localhost:8000", description="Base URL of the application")
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:8000", "http://127.0.0.1:8000"],
                                    description="Allowed CORS origins")
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:8000", "http://127.0.0.1:8000"],
                                       description="Allowed Origins for CSRF")
    CSRF_EXEMPT_ROUTES: List[str] = Field(default=["/user/login", "/user/register", "/docs", "/redoc", "/openapi.json"],
                                          description="Routes exempt from CSRF protection")

    # API Documentation
    SCHEMA_VISIBILITY: bool = Field(default=True, description="Show API docs (Swagger UI and Redoc)")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unknown variables
    )

    @field_validator("DATABASE_URL", mode="before")
    def assemble_db_url(cls, value, info):
        """
        Assemble DATABASE_URL dynamically if not provided directly.
        """
        if value:
            return value

        data = info.data
        db_name = data.get("TEST_POSTGRES_DB") if data.get("TEST_MODE") else data.get("POSTGRES_DB")

        if not all([data.get("POSTGRES_USER"), data.get("POSTGRES_PASSWORD"),
                    data.get("POSTGRES_HOST"), data.get("POSTGRES_PORT"), db_name]):
            raise ValueError("Missing database environment variables to build DATABASE_URL")

        return PostgresDsn.build(
            scheme=f"postgresql+{data.get('DB_DRIVER', 'asyncpg')}",
            username=data["POSTGRES_USER"],
            password=data["POSTGRES_PASSWORD"],
            host=data["POSTGRES_HOST"],
            port=data["POSTGRES_PORT"],
            # path=f"/{db_name}",
            path=f"{db_name}",
        )

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


# Create settings instance
settings = Settings()

# Quick debug if run directly
if __name__ == "__main__":
    import json

    print("✅ Loaded Settings:")
    print(json.dumps(settings.model_dump(), indent=4))
