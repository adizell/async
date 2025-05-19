# app/test/utils/db_test_utils.py

# Para Rodar o Script:
# pytest app/test/utils/db_test_utils.py -v

import asyncio
from typing import List, Any, Callable, TypeVar, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from app.adapters.outbound.persistence.database import AsyncSessionLocal

T = TypeVar('T')


class TestDbUtils:
    """Utilidades para testes de banco de dados."""

    @staticmethod
    async def run_parallel_operations(
            operations: List[Callable[[AsyncSession], Any]],
            session_params: Dict[str, Any] = None
    ) -> List[Any]:
        """
        Executa operações em paralelo com sessões separadas.

        Args:
            operations: Lista de funções que aceitam uma sessão e executam operações
            session_params: Parâmetros opcionais para criação de sessão

        Returns:
            Lista de resultados das operações
        """

        async def run_with_session(operation: Callable[[AsyncSession], T]) -> T:
            session = AsyncSessionLocal(**(session_params or {}))
            try:
                result = await operation(session)
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()

        # Executa todas as operações em paralelo com sessões separadas
        return await asyncio.gather(
            *[run_with_session(op) for op in operations],
            return_exceptions=True
        )
