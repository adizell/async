# app/test/integration/test_timezone_storage.py

# Para Rodar o Script:
# pytest app/test/integration/test_timezone_storage.py -v

import pytest
import uuid
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.shared.utils.datetime_utils import DateTimeUtil


@pytest.mark.asyncio
async def test_created_at_timezone(db_session: AsyncSession):
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager

    hashed_password = await UserAuthManager.hash_password("TestPassword123!")
    user_id = uuid.uuid4()
    email = f"timezone-test-{uuid.uuid4()}@example.com"

    # Get SP time and convert to UTC-naive (simulate storage)
    sp_now = DateTimeUtil.localnow()
    sp_now_for_storage = DateTimeUtil.for_storage(sp_now)

    user = User(
        id=user_id,
        email=email,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=sp_now_for_storage  # for precise comparison
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Convert DB datetime from UTC (naive) to São Paulo
    stored_sp_time = DateTimeUtil.from_storage(user.created_at)

    diff = abs((stored_sp_time - sp_now).total_seconds())
    assert diff < 5, f"Time difference too large: {diff} seconds"
    assert stored_sp_time.tzinfo.zone == 'America/Sao_Paulo'


@pytest.mark.asyncio
async def test_updated_at_timezone(db_session: AsyncSession):
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager

    hashed_password = await UserAuthManager.hash_password("TestPassword123!")
    user_id = uuid.uuid4()
    email = f"timezone-update-test-{uuid.uuid4()}@example.com"

    user = User(
        id=user_id,
        email=email,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=DateTimeUtil.for_storage(DateTimeUtil.localnow())
    )

    db_session.add(user)
    await db_session.commit()
    original_created_at = user.created_at
    original_updated_at = user.updated_at

    await asyncio.sleep(2)

    user.email = f"updated-{email}"
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.updated_at is not None
    assert user.updated_at > original_updated_at
    assert user.created_at == original_created_at

    sp_now = DateTimeUtil.localnow()
    updated_sp_time = DateTimeUtil.from_storage(user.updated_at)
    diff = abs((updated_sp_time - sp_now).total_seconds())
    assert diff < 5, f"Time difference too large: {diff} seconds"
