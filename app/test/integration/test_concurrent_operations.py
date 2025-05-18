# app/test/integration/test_concurrent_operations.py

# Para Rodar o Script:
# pytest app/test/integration/test_concurrent_operations.py -v

# Testes de Concorrência: Verificam o comportamento do sistema em operações paralelas.

import pytest
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.use_cases.user_use_cases import AsyncUserService
from app.application.dtos.user_dto import UserUpdate


@pytest.mark.asyncio
async def test_concurrent_user_updates(db_session: AsyncSession):
    """
    Testa atualizações concorrentes do mesmo usuário.
    Verifica se a segunda atualização não sobrescreve a primeira indevidamente.
    """
    # Criar usuário de teste
    user_id = uuid.uuid4()
    original_email = f"concurrent-test-{uuid.uuid4()}@example.com"

    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    user = User(
        id=user_id,
        email=original_email,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()

    # Criar duas sessões diferentes para simular atualizações concorrentes
    async def session_factory():
        from app.adapters.outbound.persistence.database import AsyncSessionLocal
        session = AsyncSessionLocal()
        try:
            yield session
        finally:
            await session.close()

    session1_gen = session_factory()
    session1 = await session1_gen.__anext__()

    session2_gen = session_factory()
    session2 = await session2_gen.__anext__()

    try:
        # Inicializar dois serviços com sessões diferentes
        service1 = AsyncUserService(session1)
        service2 = AsyncUserService(session2)

        # Preparar atualizações diferentes
        update1 = UserUpdate(email=f"update1-{uuid.uuid4()}@example.com")
        update2 = UserUpdate(is_superuser=True)

        # Executar atualizações concorrentes
        # Primeiro service1 atualiza o email
        user1 = await service1.update_user(user_id, update1)
        assert user1.email == update1.email

        # Depois service2 atualiza is_superuser
        user2 = await service2.update_user(user_id, update2)

        # Verificar se ambas as alterações foram aplicadas corretamente
        # (session2 deve carregar o email atualizado por session1)
        assert user2.email == update1.email
        assert user2.is_superuser == True

        # Verificar no banco de dados
        from app.adapters.outbound.persistence.database import AsyncSessionLocal
        verify_session = AsyncSessionLocal()
        try:
            stmt = select(User).where(User.id == user_id)
            result = await verify_session.execute(stmt)
            final_user = result.scalars().one()

            # O usuário final deve ter ambas as alterações
            assert final_user.email == update1.email
            assert final_user.is_superuser == True
        finally:
            await verify_session.close()

    finally:
        await session1.close()
        await session2.close()


@pytest.mark.asyncio
async def test_parallel_user_operations(db_session: AsyncSession):
    """
    Testa operações paralelas em diferentes usuários.
    Verifica se não há interferência entre as operações.
    """
    # Criar dois usuários de teste
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()

    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    user1 = User(
        id=user1_id,
        email=f"parallel-test1-{uuid.uuid4()}@example.com",
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )

    user2 = User(
        id=user2_id,
        email=f"parallel-test2-{uuid.uuid4()}@example.com",
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )

    db_session.add_all([user1, user2])
    await db_session.commit()

    # Preparar atualizações
    service = AsyncUserService(db_session)

    async def update_user1():
        return await service.update_user(
            user1_id,
            UserUpdate(email=f"updated1-{uuid.uuid4()}@example.com", is_superuser=True)
        )

    async def update_user2():
        return await service.update_user(
            user2_id,
            UserUpdate(email=f"updated2-{uuid.uuid4()}@example.com", is_active=False)
        )

    # Executar atualizações em paralelo
    user1_result, user2_result = await asyncio.gather(update_user1(), update_user2())

    # Verificar resultados
    assert user1_result.is_superuser == True
    assert user2_result.is_active == False

    # Verificar que os emails foram atualizados corretamente
    assert user1_result.email.startswith("updated1-")
    assert user2_result.email.startswith("updated2-")
