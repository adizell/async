# migrations/env.py

import os
import sys
import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Ajuste do caminho para importar a aplicação
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.adapters.configuration.config import settings
from app.adapters.outbound.persistence.models import Base

# Variáveis principais
target_metadata = Base.metadata

# Configuração de logging
fileConfig(context.config.config_file_name)

# Obtenha a URL de conexão
DB_URL = str(settings.DATABASE_URL)
SYNC_DB_URL = DB_URL.replace("+asyncpg", "+psycopg2")


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    """
    url = SYNC_DB_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_synchronous_migrations() -> None:
    """
    Run migrations with a synchronous engine.
    This is used for all Alembic commands to avoid async issues.
    """
    configuration = context.config.get_section(context.config.config_ini_section)
    configuration["sqlalchemy.url"] = SYNC_DB_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# Para qualquer comando do Alembic, usar sempre a abordagem síncrona
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_synchronous_migrations()
