# app/shared/middleware/error_handler_middleware.py

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.domain.exceptions import DomainException
import logging

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        # 1. Exceções customizadas do domínio
        except DomainException as e:
            logger.warning(f"[{e.internal_code}] DomainException: {e.message}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "error": e.message,
                    "code": e.internal_code,
                    "details": e.details,
                },
            )

        # 2. Erros de validação (Pydantic/FastAPI)
        except RequestValidationError as e:
            logger.warning("RequestValidationError")
            return JSONResponse(
                status_code=422,
                content={
                    "success": False,
                    "error": "Erro de validação nos dados enviados.",
                    "code": "VALIDATION_ERROR",
                    "details": e.errors(),
                },
            )

        # 3. Exceções HTTP padrão (como HTTPException 404, etc.)
        except HTTPException as e:
            logger.warning(f"HTTPException: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "success": False,
                    "error": str(e.detail),
                    "code": "HTTP_EXCEPTION",
                },
            )

        # 4. Erros inesperados
        except Exception as e:
            logger.exception(f"Erro inesperado em {request.url.path}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Erro interno do servidor.",
                    "code": "INTERNAL_SERVER_ERROR",
                },
            )
