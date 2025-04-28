# app/test/routes/test_authentication_flow.py

# Para Rodar o Script:
# pytest app/test/routes/test_authentication_flow.py -v

import uuid
import pytest
from sqlalchemy import select
from app.adapters.outbound.persistence.models.user_model import User


# 🔥 Fixture interna só para gerar dados do usuário dinamicamente
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

    # Limpar usuário antes
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    existing_user = result.unique().scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # Registrar usuário
    response = await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)
    assert response.status_code in (200, 201), f"Erro no registro: {response.text}"


@pytest.mark.asyncio
async def test_user_login(async_client, test_client_token):
    """
    Testa se login de usuário retorna access_token e refresh_token.
    """
    user_data = generate_user_data(email="login_user_test@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # Primeiro registra
    await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)

    # Agora faz login
    response = await async_client.post("/api/v1/auth/login", json=user_data, headers=headers)
    assert response.status_code == 200, f"Erro no login: {response.text}"

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_user_me(async_client, test_user_and_token):
    """
    Testa se o usuário autenticado consegue acessar o próprio perfil (/user/me).
    """
    _, access_token = test_user_and_token
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await async_client.get("/api/v1/user/me", headers=headers)

    # Valida se a requisição foi bem sucedida
    assert response.status_code == 200, f"Erro ao acessar perfil: {response.text}"

    response_data = response.json()

    # Verifica se o JSON retornou os campos esperados
    assert response_data is not None, "Resposta vazia."
    assert "email" in response_data, "Campo 'email' não encontrado na resposta."
    assert "id" in response_data, "Campo 'id' não encontrado na resposta."
    assert isinstance(response_data["email"], str), "Email deveria ser uma string."


@pytest.mark.asyncio
async def test_user_update(async_client, test_user_and_token):
    """
    Testa se um usuário autenticado pode atualizar seus próprios dados (ex: email).
    """
    user_data, access_token = test_user_and_token
    headers = {"Authorization": f"Bearer {access_token}"}

    new_email = "updated_email@example.com"

    update_data = {
        "email": new_email
    }

    response = await async_client.put("/api/v1/user/me", json=update_data, headers=headers)
    assert response.status_code == 200, f"Erro ao atualizar usuário: {response.text}"

    response_data = response.json()
    assert response_data is not None, "Resposta vazia."
    assert response_data.get("email") == new_email, "Email não foi atualizado corretamente."


@pytest.mark.asyncio
async def test_user_refresh(async_client, test_user_and_token, test_client_token):
    """
    Testa se o refresh_token gera novo access_token corretamente.
    """
    user_data, _ = test_user_and_token

    # Cabeçalho de autorização para login (Client Token)
    login_headers = {"Authorization": f"Bearer {test_client_token}"}

    # Fazer login para pegar refresh_token
    response_login = await async_client.post("/api/v1/auth/login", json=user_data, headers=login_headers)
    assert response_login.status_code == 200, f"Erro no login: {response_login.text}"

    login_data = response_login.json()
    refresh_token = login_data.get("refresh_token")
    assert refresh_token is not None, "Refresh token não retornado."

    # 🛠 Cabeçalho de autorização para refresh (continua Client Token, e NÃO access_token do usuário)
    refresh_headers = {"Authorization": f"Bearer {test_client_token}"}

    # Fazer refresh
    response_refresh = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
        headers=refresh_headers
    )
    assert response_refresh.status_code == 200, f"Erro no refresh: {response_refresh.text}"

    tokens = response_refresh.json()
    assert "access_token" in tokens, "Novo access_token não retornado no refresh."
    assert "refresh_token" in tokens, "Novo refresh_token não retornado no refresh."

