# app/test/routes/test_authentication_flow.py

# Para Rodar o Script:
# pytest app/test/routes/test_authentication_flow.py -v

import uuid
import pytest
from sqlalchemy import select
from app.adapters.outbound.persistence.models.user_model import User


# 🔥 Função auxiliar para gerar dados de usuário dinamicamente
def generate_user_data(email="test_user_auth@example.com"):
    return {
        "email": email,
        "password": "StrongP@ssword123"
    }


@pytest.mark.asyncio
async def test_user_register(async_client, db_session, test_client_token):
    """
    Testa se um novo usuário pode ser registrado.
    """
    user_data = generate_user_data(email="register_user_test@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # 🔎 Limpar usuário antes do teste (caso já exista)
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.unique().scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # 🛠️ Fazer o registro
    response = await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)
    assert response.status_code in (200, 201), f"Erro no registro: {response.text}"


@pytest.mark.asyncio
async def test_user_login(async_client, db_session, test_client_token):
    """
    Testa se login de usuário retorna access_token e refresh_token.
    """
    user_data = generate_user_data(email="login_user_test@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # 🔎 Limpar usuário antes
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.unique().scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # 🛠️ Registrar usuário
    await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)

    # 🛠️ Login com as credenciais do usuário registrado
    response = await async_client.post("/api/v1/auth/login", json=user_data, headers=headers)
    assert response.status_code == 200, f"Erro no login: {response.text}"

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_user_me(async_client, db_session, test_client_token):
    """
    Testa se o usuário autenticado consegue acessar seu próprio perfil (/user/me).
    """
    user_data = generate_user_data(email="me_user_test@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # 🔎 Limpar usuário antes
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.unique().scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # 🛠️ Registrar usuário
    await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)

    # 🛠️ Login para pegar access_token do usuário
    login_response = await async_client.post("/api/v1/auth/login", json=user_data, headers=headers)
    assert login_response.status_code == 200, f"Erro ao fazer login: {login_response.text}"
    access_token = login_response.json()["access_token"]

    user_headers = {"Authorization": f"Bearer {access_token}"}

    # 🛠️ Testar o /me
    response = await async_client.get("/api/v1/user/me", headers=user_headers)
    assert response.status_code == 200, f"Erro ao acessar perfil: {response.text}"

    response_data = response.json()
    assert "email" in response_data
    assert "id" in response_data


@pytest.mark.asyncio
async def test_user_update(async_client, db_session, test_client_token):
    """
    Testa se o usuário autenticado consegue atualizar seus próprios dados.
    """
    user_data = generate_user_data(email="update_user_test@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # 🔎 Limpar usuário antes
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.unique().scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # 🛠️ Registrar usuário
    await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)

    # 🛠️ Login para pegar access_token
    login_response = await async_client.post("/api/v1/auth/login", json=user_data, headers=headers)
    assert login_response.status_code == 200, f"Erro ao fazer login: {login_response.text}"
    access_token = login_response.json()["access_token"]

    user_headers = {"Authorization": f"Bearer {access_token}"}

    # 🛠️ Atualizar dados do usuário
    new_email = "updated_user_test@example.com"
    update_data = {"email": new_email}

    response = await async_client.put("/api/v1/user/me", json=update_data, headers=user_headers)
    assert response.status_code == 200, f"Erro ao atualizar usuário: {response.text}"

    response_data = response.json()
    assert response_data["email"] == new_email


@pytest.mark.asyncio
async def test_user_refresh(async_client, db_session, test_client_token):
    """
    Testa se o usuário consegue gerar novo access_token com refresh_token.
    """
    user_data = generate_user_data(email="refresh_user_test@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # 🔎 Limpar usuário antes
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.unique().scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # 🛠️ Registrar usuário
    await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)

    # 🛠️ Login para pegar refresh_token
    login_response = await async_client.post("/api/v1/auth/login", json=user_data, headers=headers)
    assert login_response.status_code == 200, f"Erro ao fazer login: {login_response.text}"

    login_data = login_response.json()
    refresh_token = login_data.get("refresh_token")
    assert refresh_token, "Refresh token não retornado."

    # 🛠️ Realizar refresh do token
    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
        headers=headers
    )
    assert response.status_code == 200, f"Erro no refresh token: {response.text}"

    refreshed_data = response.json()
    assert "access_token" in refreshed_data
    assert "refresh_token" in refreshed_data
