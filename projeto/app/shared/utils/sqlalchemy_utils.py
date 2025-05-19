# app/shared/utils/sqlalchemy_utils.py

from typing import TypeVar, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine.result import Result

T = TypeVar('T')


class SQLAlchemyUtils:
    """Utilitário para operações comuns com SQLAlchemy."""

    @staticmethod
    async def execute_and_scalars(session: AsyncSession, statement: Any) -> Result:
        """Executa uma query e retorna um Result já com unique() aplicado."""
        result = await session.execute(statement)
        return result.unique()

    @staticmethod
    async def execute_scalars_all(session: AsyncSession, statement: Any) -> List[T]:
        """Executa uma query e retorna todos os resultados como uma lista."""
        result = await session.execute(statement)
        return result.scalars().unique().all()

    @staticmethod
    async def execute_scalar_one_or_none(session: AsyncSession, statement: Any) -> Optional[T]:
        """Executa uma query e retorna um único resultado ou None."""
        result = await session.execute(statement)
        return result.scalars().unique().one_or_none()
