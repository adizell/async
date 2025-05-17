# app/shared/middleware/hybrid_auth_middleware.py

"""
Middleware para autenticação híbrida (cookie e bearer).

Este middleware verifica o tipo de autenticação configurada e redireciona
para o modo apropriado: cookie, bearer, ou ambos dependendo da configuração.
"""

import logging
from typing import Callable, Awaitable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Scope, Receive, Send

from app.adapters.configuration.config import settings

# Configurar logger
logger = logging.getLogger(__name__)


class HybridAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware para gerenciar diferentes modos de autenticação.

    Baseado no valor de AUTH_MODE nas configurações, este middleware
    pode configurar a aplicação para usar:
    - bearer: Apenas autenticação via token no header Authorization
    - cookie: Apenas autenticação via cookies
    - hybrid: Suporta ambos os modos (cookie e bearer)
    """

    async def dispatch(
            self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Processa a requisição e configura a autenticação apropriada.

        Args:
            request: Objeto Request do FastAPI
            call_next: Próxima função no pipeline de middlewares

        Returns:
            Response: Resposta HTTP
        """
        # Adiciona o modo de autenticação aos metadados do request
        # para que possa ser acessado pelos handlers
        request.state.auth_mode = settings.AUTH_MODE

        # Adiciona informações de debug no header da resposta
        response = await call_next(request)
        response.headers["X-Auth-Mode"] = settings.AUTH_MODE

        return response


class AuthASGIMiddleware:
    """
    Versão ASGI do middleware de autenticação híbrida.
    Mais eficiente por não duplicar a classe Request.
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self.auth_mode = settings.AUTH_MODE

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            # Passa através para websockets e outros protocolos
            await self.app(scope, receive, send)
            return

        # Adiciona o modo de autenticação ao escopo
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["auth_mode"] = self.auth_mode

        # Substitui a função send original para adicionar headers
        original_send = send

        async def wrapped_send(message: Dict[str, Any]):
            if message["type"] == "http.response.start":
                # Adiciona informações de debug no header
                if "headers" not in message:
                    message["headers"] = []

                # Converte a string para bytes para o formato ASGI
                message["headers"].append(
                    (b"X-Auth-Mode", self.auth_mode.encode())
                )

            await original_send(message)

        # Continua o processamento com a função send modificada
        await self.app(scope, receive, wrapped_send)
