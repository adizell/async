# app/main.py (async version)

import os
import logging
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager

from app.adapters.configuration.config import settings
from app.adapters.inbound.api.v1.endpoints import client_endpoint
from app.adapters.outbound.persistence.database import engine, Base
from app.adapters.inbound.api.v1.router import api_router as api_v1_router
from app.shared.middleware.hybrid_auth_middleware import HybridAuthMiddleware
from app.shared.middleware.error_handler_middleware import ErrorHandlerMiddleware
from app.adapters.outbound.persistence.models.user_group.base_model import register_password_protection

# ─── UNIQUE LOGGING CONFIGURATION ─────────────────────────────────────────────────
level = logging.DEBUG if settings.DEBUG else getattr(logging, settings.LOG_LEVEL, logging.INFO)
logging.basicConfig(
    level=level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")

    # Registrar eventos de proteção de senha
    register_password_protection()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.cleanup_task = asyncio.create_task(periodic_cleanup())
    yield
    logger.info("Application shutting down...")
    app.state.cleanup_task.cancel()
    try:
        await app.state.cleanup_task
    except asyncio.CancelledError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")

    # Registrar todos os eventos
    from app.adapters.outbound.persistence.models.user_group.base_model import register_all_events
    register_all_events()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.cleanup_task = asyncio.create_task(periodic_cleanup())
    yield
    logger.info("Application shutting down...")
    app.state.cleanup_task.cancel()
    try:
        await app.state.cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="ADIZELL",
    description="FastAPI Hexagonal Async",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Static files (somente monta se a pasta existir)
if os.path.isdir("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
else:
    logger.warning("Static directory 'app/static' does not exist. Skipping static files mounting.")

# Middlewares
from app.shared.middleware import (
    AsyncExceptionMiddleware,
    AsyncRequestLoggingMiddleware,
    AsyncCSRFProtectionMiddleware,
    AsyncRateLimitingMiddleware,
    AsyncSecurityHeadersMiddleware
)

app.add_middleware(HybridAuthMiddleware)
app.add_middleware(AsyncSecurityHeadersMiddleware)
app.add_middleware(AsyncCSRFProtectionMiddleware)
app.add_middleware(AsyncRequestLoggingMiddleware)
app.add_middleware(AsyncRateLimitingMiddleware)
app.add_middleware(AsyncExceptionMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# Routers
app.include_router(client_endpoint.jwt_router)
app.include_router(client_endpoint.create_url_router)
app.include_router(client_endpoint.update_url_router)
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/img/favicon.ico")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    spec = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for schema in ("HTTPValidationError", "ValidationError"):
        spec.get("components", {}).get("schemas", {}).pop(schema, None)
    for path in spec.get("paths", {}).values():
        for op in path.values():
            op.get("responses", {}).pop("422", None)
    app.openapi_schema = spec
    return spec


app.openapi = custom_openapi


# ── TOKEN BLACKLIST CLEANUP TASK ──────────────────────────────────────────────
async def cleanup_token_blacklist():
    from app.adapters.outbound.persistence.database import get_db_context
    from app.adapters.outbound.persistence.repositories.token_repository import token_repository
    async with get_db_context() as db:
        deleted = await token_repository.cleanup_expired(db)
        logger.info(f"Cleaned up {deleted} expired tokens from blacklist")


async def periodic_cleanup():
    while True:
        try:
            await cleanup_token_blacklist()
            await asyncio.sleep(24 * 60 * 60)
        except asyncio.CancelledError:
            logger.info("Token cleanup task cancelled")
            break
        except Exception as e:
            logger.exception(f"Error in cleanup_token_blacklist: {e}")
