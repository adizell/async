# app/test/conftest.py

import asyncio
import datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_

from app.adapters.inbound.api.deps import logger
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
    Cria um novo usuário através da API e retorna (user_data, access_token)
    """
    # Dados do usuário para teste
    password_raw = "TestPassword123!"
    user_data = {
        "email": f"usertest-{uuid4()}@example.com",
        "password": password_raw
    }

    headers = {"Authorization": f"Bearer {test_client_token}"}

    # Registrar o usuário
    response_register = await async_client.post(
        "/api/v1/auth/register",
        json=user_data,
        headers=headers
    )
    assert response_register.status_code in (200, 201), f"Erro ao registrar usuário: {response_register.text}"

    # Fazer login para obter o access token
    response_login = await async_client.post(
        "/api/v1/auth/login",
        json=user_data,
        headers=headers
    )
    assert response_login.status_code == 200, f"Erro ao fazer login: {response_login.text}"

    tokens = response_login.json()
    access_token = tokens["access_token"]

    return user_data, access_token


# Criação de usuário de teste
@pytest_asyncio.fixture
async def create_test_user(db_session: AsyncSession):
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager

    # Gerar senha criptografada
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    # Criar usuário com senha já criptografada
    user = User(
        id=uuid4(),
        email=f"usertest-{uuid4()}@example.com",
        password=hashed_password,  # Senha já criptografada
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture(autouse=True)
async def cleanup_after_test(db_session: AsyncSession):
    """
    Fixture para limpar o banco de dados após cada teste.
    O parâmetro autouse=True garante que esta fixture seja executada
    automaticamente para todos os testes.
    """
    # Primeiro, permitir que o teste seja executado
    yield

    # Após o teste, limpar os dados criados durante os testes
    try:
        # Limpar usuários de teste (que contêm 'test' ou padrões específicos no email)
        await db_session.execute(
            delete(User).where(
                or_(
                    User.email.like("%test%"),
                    User.email.like("%example.com"),
                    # Outros padrões de identificação de dados de teste
                    User.email.like("userdeactivate-%"),
                    User.email.like("userreactivate-%"),
                    User.email.like("superuser-%")
                )
            )
        )

        # Limpar tokens na blacklist criados durante os testes
        # Se houver uma tabela de tokens na blacklist
        # await db_session.execute(delete(TokenBlacklist).where(...))

        # Limpar outros dados de teste em outras tabelas conforme necessário
        # await db_session.execute(delete(Client).where(Client.client_id.like("%test%")))

        # Confirmar as alterações
        await db_session.commit()

    except Exception as e:
        # Em caso de erro, fazer rollback e registrar
        await db_session.rollback()
        logger.error(f"Erro ao limpar dados após teste: {str(e)}")
        raise
