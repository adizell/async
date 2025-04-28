# app/shared/middleware/logging_middleware.py (async version)

"""
Middleware for HTTP request logging.

This module implements a middleware that logs information
about received requests and sent responses.
"""

import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.adapters.configuration.config import settings

# Configure logger
logger = logging.getLogger(__name__)


class AsyncRequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request logging.
    Logs information about each received request.
    """

    async def dispatch(self, request: Request, call_next):
        # Log the request - with limited information in production
        if settings.ENVIRONMENT == "production":
            logger.info(f"Request: {request.method} {request.url.path}")
        else:
            # In development, can include more details like query params
            query_params = dict(request.query_params)
            logger.info(
                f"Request: {request.method} {request.url.path} | "
                f"Query: {query_params if query_params else 'N/A'} | "
                f"Client: {request.client.host if request.client else 'N/A'}"
            )

        # Process the request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log the response
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
    Middleware que verifica se as senhas estão sendo corretamente criptografadas
    antes de serem salvas no banco de dados.
    """

    @staticmethod
    async def before_insert_or_update(
            mapper, connection, target
    ) -> None:
        """
        Evento disparado antes de qualquer operação de insert/update
        que verifica se o campo password não contém uma senha em texto plano.
        """
        from app.adapters.outbound.security.auth_user_manager import UserAuthManager
        import re

        # Se o modelo tem um campo password
        if hasattr(target, 'password') and target.password:
            # Padrão para bcrypt hash ($2b$...)
            bcrypt_pattern = re.compile(r'^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$')

            # Se não parece um hash bcrypt, é provável que seja texto plano
            if not bcrypt_pattern.match(target.password):
                # Log de segurança
                logger.error(f"TENTATIVA DE SALVAR SENHA EM TEXTO PLANO BLOQUEADA: {target.__class__.__name__}")

                # Criptografar automaticamente
                target.password = await UserAuthManager.hash_password(target.password)
