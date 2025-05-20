# app/shared/middleware/logging_middleware.py (async version)

"""
Middleware for HTTP request logging.

This module implements a middleware that logs information
about received requests and sent responses.
"""

# app/shared/middleware/logging_middleware.py (async version)

"""
Middleware for HTTP request logging and password protection.
"""

import time
import logging
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.adapters.configuration.config import settings
from app.adapters.outbound.security.auth_user_manager import UserAuthManager

# Configure logger
logger = logging.getLogger(__name__)


class AsyncRequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para log de requisições HTTP.
    """

    async def dispatch(self, request: Request, call_next):
        # Log da requisição
        if settings.ENVIRONMENT == "production":
            logger.info(f"Request: {request.method} {request.url.path}")
        else:
            query_params = dict(request.query_params)
            logger.info(
                f"Request: {request.method} {request.url.path} | "
                f"Query: {query_params if query_params else 'N/A'} | "
                f"Client: {request.client.host if request.client else 'N/A'}"
            )

        # Processar
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log da resposta
        if settings.ENVIRONMENT == "production":
            logger.info(f"Response: {response.status_code} for {request.method} {request.url.path}")
        else:
            logger.info(
                f"Response: {response.status_code} for {request.method} {request.url.path} | "
                f"Time: {process_time:.4f}s"
            )

        return response


class PasswordProtectionMiddleware:
    """
    Middleware de proteção de senha: evita salvar senha em texto plano no banco.
    Deve ser registrado nos eventos before_insert e before_update do ORM.
    """

    @staticmethod
    def before_insert_or_update(mapper, connection, target) -> None:
        """
        Hook ORM síncrono (SQLAlchemy): executado antes de insert/update.
        """
        if hasattr(target, 'password') and target.password:
            bcrypt_pattern = re.compile(r'^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$')

            if not bcrypt_pattern.match(target.password):
                logger.warning(
                    f"[PasswordProtectionMiddleware] Detected plain text password in model {target.__class__.__name__}. "
                    "Automatically hashing before saving."
                )
                target.password = UserAuthManager.hash_password_sync(target.password)
