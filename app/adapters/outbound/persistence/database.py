# app/adapters/outbound/persistence/database.py

"""
Configuração de conexão com banco de dados.

Gerencia engines e sessions (sync e async) para o PostgreSQL,
configura pools, eventos e fornece funções de dependência para FastAPI.
"""

import time
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import event, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, Session as SyncSession
from sqlalchemy.pool import QueuePool

from app.adapters.configuration.config import settings

logger = logging.getLogger(__name__)


# --- Eventos de monitoramento de performance e reconnect ---

def handle_disconnect(dbapi_conn, conn_rec, conn_proxy):
    try:
        if hasattr(dbapi_conn, "ping"):
            dbapi_conn.ping(reconnect=True, attempts=3, delay=5)
    except Exception as e:
        conn_rec.invalidate(e)
        logger.warning(f"Conexão invalidada: {e}")


def before_cursor_execute(conn, cursor, stmt, params, ctx, executemany):
    conn.info.setdefault("query_start_time", time.time())
    if settings.ENVIRONMENT == "development":
        logger.debug(f"SQL: {stmt}")


def after_cursor_execute(conn, cursor, stmt, params, ctx, executemany):
    total = time.time() - conn.info.pop("query_start_time", time.time())
    if total > 0.5:
        logger.warning(f"Query lenta ({total:.2f}s): {stmt}")
    elif settings.ENVIRONMENT == "development":
        logger.debug(f"Query executada em {total:.2f}s")


# --- Construção das URLs e Engines ---

# Assíncrono usa asyncpg; síncrono substitui por psycopg2
DATABASE_URL_ASYNC = str(settings.DATABASE_URL)
DATABASE_URL_SYNC = DATABASE_URL_ASYNC.replace("+asyncpg", "+psycopg2")

logger.info(f"[ASYNC] Conectando ao DB em: {DATABASE_URL_ASYNC.split('@')[-1]}")
logger.info(f"[SYNC] Conectando ao DB em: {DATABASE_URL_SYNC.split('@')[-1]}")

# Engine síncrono (para scripts ou use_cases sync)
sync_engine = create_engine(
    DATABASE_URL_SYNC,
    poolclass=QueuePool,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
    future=True,
)
event.listen(sync_engine, "checkout", handle_disconnect)
event.listen(sync_engine, "before_cursor_execute", before_cursor_execute)
event.listen(sync_engine, "after_cursor_execute", after_cursor_execute)

# Engine assíncrono (para endpoints async)
async_engine: AsyncEngine = create_async_engine(
    DATABASE_URL_ASYNC,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
    future=True,
)
# Registrar eventos no sync_engine interno do async_engine
event.listen(async_engine.sync_engine, "checkout", handle_disconnect)
event.listen(async_engine.sync_engine, "before_cursor_execute", before_cursor_execute)
event.listen(async_engine.sync_engine, "after_cursor_execute", after_cursor_execute)

# --- Session factories ---

# Síncrono
SessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=SyncSession,
)

# Assíncrono
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

logger.info("Engines e sessions configurados com sucesso")


# --- Dependências e context managers ---

@contextmanager
def get_sync_db() -> Generator[SyncSession, None, None]:
    """
    Context manager para sessões síncronas.
    Uso em scripts ou em use_cases sync.
    """
    db: SyncSession = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """
    Dependência FastAPI para endpoints async.
    Use: async def endpoint(db: AsyncSession = Depends(get_async_db))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise


def get_db() -> Generator[SyncSession, None, None]:
    """
    Dependência FastAPI para endpoints síncronos.
    Use: def endpoint(db: SyncSession = Depends(get_db))
    """
    with get_sync_db() as db:
        yield db
