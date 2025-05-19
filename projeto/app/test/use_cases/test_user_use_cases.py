# app/test/use_cases/test_user_use_cases.py

# pytest app/test/use_cases/test_user_use_cases.py
# pytest app/test/use_cases/test_user_use_cases.py::test_list_users
# pytest app/test/use_cases/test_user_use_cases.py::test_update_user
# pytest app/test/use_cases/test_user_use_cases.py::test_deactivate_user
# pytest app/test/use_cases/test_user_use_cases.py::test_reactivate_user
# pytest app/test/use_cases/test_user_use_cases.py::test_delete_user_permanently

# pytest app/test/use_cases/test_user_use_cases.py::test_dummy_user_use_case
# @pytest.mark.asyncio
# async def test_dummy_user_use_case():
#     assert 1 + 1 == 2


import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select
from fastapi_pagination import Params

from app.adapters.outbound.persistence.models import User
from app.application.use_cases.user_use_cases import AsyncUserService
from app.application.dtos.user_dto import UserUpdate
from app.adapters.outbound.security.auth_user_manager import UserAuthManager


@pytest_asyncio.fixture(scope="function")
async def hashed_test_password() -> str:
    """
    Gera e fornece uma senha criptografada para uso em cada teste.
    """
    return await UserAuthManager.hash_password("TestPassword123!")



@pytest.mark.asyncio
async def test_list_users(db_session, hashed_test_password: str):
    """
    Testa a listagem de usuários, garantindo que o serviço retorna uma lista válida.
    """
    unique_email = f"superuser-{uuid4()}@example.com"

    superuser = User(
        id=uuid4(),
        email=unique_email,
        password=hashed_test_password,
        is_active=True,
        is_superuser=True,
        created_at=datetime.utcnow()
    )
    db_session.add(superuser)
    await db_session.commit()
    await db_session.refresh(superuser)

    service = AsyncUserService(db_session)
    params = Params(page=1, size=10)

    result = await service.list_users(current_user=superuser, params=params, order="desc")

    assert result.items is not None
    assert isinstance(result.items, list)


@pytest.mark.asyncio
async def test_update_user(db_session, hashed_test_password: str):
    """
    Testa a atualização de dados de um usuário existente.
    """
    unique_email = f"olduser-{uuid4()}@example.com"

    user = User(
        id=uuid4(),
        email=unique_email,
        password=hashed_test_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = AsyncUserService(db_session)

    update_data = UserUpdate(
        email=f"newuser-{uuid4()}@example.com",
        is_active=False,
        is_superuser=True
    )

    updated_user = await service.update_user(user.id, update_data)

    assert updated_user.email.startswith("newuser-")
    assert updated_user.is_active is False
    assert updated_user.is_superuser is True


@pytest.mark.asyncio
async def test_deactivate_user(db_session, hashed_test_password: str):
    """
    Testa a desativação segura de um usuário.
    """
    user = User(
        id=uuid4(),
        email=f"userdeactivate-{uuid4()}@example.com",
        password=hashed_test_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = AsyncUserService(db_session)

    result = await service.deactivate_user(user.id)

    assert result["message"].startswith("User")
    assert "successfully deactivated" in result["message"]

    await db_session.refresh(user)
    assert user.is_active is False


@pytest.mark.asyncio
async def test_reactivate_user(db_session, hashed_test_password: str):
    """
    Testa a reativação de um usuário previamente desativado.
    """
    user = User(
        id=uuid4(),
        email=f"userreactivate-{uuid4()}@example.com",
        password=hashed_test_password,
        is_active=False,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = AsyncUserService(db_session)

    result = await service.reactivate_user(user.id)

    assert result["message"].startswith("User")
    assert "successfully reactivated" in result["message"]

    await db_session.refresh(user)
    assert user.is_active is True


@pytest.mark.asyncio
async def test_delete_user_permanently(db_session, hashed_test_password: str):
    """
    Testa a deleção permanente de um usuário.
    """
    user = User(
        id=uuid4(),
        email=f"userdelete-{uuid4()}@example.com",
        password=hashed_test_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = AsyncUserService(db_session)

    result = await service.delete_user_permanently(user.id)

    assert result["message"].startswith("User")
    assert "permanently deleted" in result["message"]

    stmt = select(User).where(User.id == user.id)
    user_deleted = (await db_session.execute(stmt)).scalars().first()
    assert user_deleted is None
