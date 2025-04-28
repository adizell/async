# app/test/conftest.py

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.main import app
from dotenv import load_dotenv
from app.adapters.outbound.persistence.database import get_db
from app.adapters.outbound.persistence.models.client_model import Client
from app.adapters.outbound.persistence.models.user_model import User
from app.adapters.outbound.persistence.repositories.client_repository import client_repository
from app.adapters.outbound.security.auth_client_manager import ClientAuthManager

# Carrega o .env
load_dotenv(dotenv_path=".env")


@pytest.fixture(scope="session")
def event_loop():
    """Um único loop para todos os testes assíncronos."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_client(db_session):
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    session_gen = get_db()
    session = await session_gen.__anext__()
    try:
        yield session
    finally:
        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.aclose()


@pytest_asyncio.fixture
async def test_client_token(db_session: AsyncSession) -> str:
    """
    Cria um novo client e gera token para cada teste.
    """
    credentials = await client_repository.create_with_credentials(db_session)
    client_id = credentials["client_id"]

    stmt = select(Client).where(Client.client_id == client_id)
    result = await db_session.execute(stmt)
    client = result.scalar_one()

    token = await ClientAuthManager.create_client_token(subject=str(client.id))
    return token


@pytest_asyncio.fixture
async def test_user_and_token(async_client: AsyncClient, db_session: AsyncSession, test_client_token: str):
    """
    Cria um novo usuário e retorna (user_data, access_token)
    """
    user_data = {
        "email": "test_user_token@example.com",
        "password": "StrongP@ssword123"
    }
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # Deletar usuário se já existir
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.unique().scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # Registrar usuário
    response = await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)
    assert response.status_code in (200, 201), f"Erro ao registrar usuário: {response.text}"

    # Fazer login
    headers = {"Authorization": f"Bearer {test_client_token}"}
    response_login = await async_client.post("/api/v1/auth/login", json=user_data, headers=headers)
    assert response_login.status_code == 200, f"Erro ao fazer login: {response_login.text}"

    tokens = response_login.json()
    access_token = tokens["access_token"]

    return user_data, access_token
