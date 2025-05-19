# app/test/integration/test_concurrent_operations.py

import pytest
import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.use_cases.user_use_cases import AsyncUserService
from app.application.dtos.user_dto import UserUpdate
from app.shared.utils.datetime_utils import DateTimeUtil


@pytest.mark.asyncio
async def test_concurrent_user_updates(db_session: AsyncSession):
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
        created_at=DateTimeUtil.utcnow_naive()
    )
    db_session.add(user)
    await db_session.commit()

    from app.adapters.outbound.persistence.database import AsyncSessionLocal

    session1 = await AsyncSessionLocal().__aenter__()
    session2 = await AsyncSessionLocal().__aenter__()

    try:
        service1 = AsyncUserService(session1)
        service2 = AsyncUserService(session2)

        update1 = UserUpdate(email=f"update1-{uuid.uuid4()}@example.com")
        update2 = UserUpdate(is_superuser=True)

        user1 = await service1.update_user(user_id, update1)
        assert user1.email == update1.email

        user2 = await service2.update_user(user_id, update2)
        assert user2.email == update1.email
        assert user2.is_superuser is True

        verify_session = await AsyncSessionLocal().__aenter__()
        try:
            stmt = select(User).where(User.id == user_id)
            result = await verify_session.execute(stmt)
            final_user = result.scalars().unique().one()

            assert final_user.email == update1.email
            assert final_user.is_superuser is True
        finally:
            await verify_session.close()
    finally:
        await session1.close()
        await session2.close()


@pytest.mark.asyncio
async def test_parallel_user_operations(db_session: AsyncSession):
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
        created_at=DateTimeUtil.utcnow_naive()
    )
    user2 = User(
        id=user2_id,
        email=f"parallel-test2-{uuid.uuid4()}@example.com",
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=DateTimeUtil.utcnow_naive()
    )

    db_session.add_all([user1, user2])
    await db_session.commit()

    from app.adapters.outbound.persistence.database import AsyncSessionLocal
    session1 = await AsyncSessionLocal().__aenter__()
    session2 = await AsyncSessionLocal().__aenter__()

    try:
        service1 = AsyncUserService(session1)
        service2 = AsyncUserService(session2)

        results = await asyncio.gather(
            service1.update_user(user1_id, UserUpdate(email=f"updated1-{uuid.uuid4()}@example.com", is_superuser=True)),
            service2.update_user(user2_id, UserUpdate(email=f"updated2-{uuid.uuid4()}@example.com", is_active=False)),
            return_exceptions=True
        )

        for result in results:
            if isinstance(result, Exception):
                raise result

        user1_result, user2_result = results
        assert user1_result.is_superuser is True
        assert user2_result.is_active is False
        assert user1_result.email.startswith("updated1-")
        assert user2_result.email.startswith("updated2-")

    finally:
        await session1.close()
        await session2.close()
