# app/test/routes/user_group/test_auth_edge_cases.py

# Para rodar:
# pytest app/test/routes/user_group/test_auth_edge_cases.py -v

import pytest
from sqlalchemy import select
from app.adapters.outbound.persistence.models.user_group.user_model import User


# 🔥 Fixture auxiliar para gerar dados válidos de usuário
def generate_user_data(email="user_edgecase@example.com"):
    return {
        "email": email,
        "password": "ValidP@ssword123"
    }


@pytest.mark.asyncio
async def test_login_wrong_password(async_client, db_session, test_client_token):
    """
    Testa login com senha errada (usuário existe).
    Deve retornar 401 Unauthorized.
    """
    user_data = generate_user_data(email="wrong_password@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # Garante que o usuário existe
    await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)

    # Tenta logar com senha errada
    login_data = {
        "email": user_data["email"],
        "password": "WrongPassword123"
    }
    response = await async_client.post("/api/v1/auth/login", json=login_data, headers=headers)

    assert response.status_code == 401, f"Status deveria ser 401, veio: {response.status_code}"
    assert "Incorrect email or password" in response.text


@pytest.mark.asyncio
async def test_login_missing_field(async_client, test_client_token):
    """
    Testa login sem fornecer o campo 'password'.
    Deve retornar 422 Unprocessable Entity.
    """
    headers = {"Authorization": f"Bearer {test_client_token}"}

    login_data = {
        "email": "missingfield@example.com"
        # ❌ Sem o campo 'password'
    }

    response = await async_client.post("/api/v1/auth/login", json=login_data, headers=headers)

    assert response.status_code == 422, f"Status deveria ser 422, veio: {response.status_code}"
    assert "password" in response.text


@pytest.mark.asyncio
async def test_login_inactive_user(async_client, db_session, test_client_token):
    """
    Testa login com usuário inativo.
    Deve retornar 401 Unauthorized.
    """
    user_data = generate_user_data(email="inactive_user@example.com")
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # Registra o usuário
    await async_client.post("/api/v1/auth/register", json=user_data, headers=headers)

    # Torna o usuário inativo diretamente no banco
    result = await db_session.execute(select(User).where(User.email == user_data["email"]))
    user = result.unique().scalar_one()
    user.is_active = False
    await db_session.commit()

    # Tenta login com usuário inativo
    response = await async_client.post("/api/v1/auth/login", json=user_data, headers=headers)

    assert response.status_code == 401, f"Status deveria ser 401, veio: {response.status_code}"
    assert "Inactive user" in response.text or "inactive" in response.text.lower()


@pytest.mark.asyncio
async def test_logout_token(async_client, test_user_and_token):
    """
    Testa logout do usuário (revogar access_token atual).
    Deve retornar 200 OK.
    """
    _, access_token = test_user_and_token
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await async_client.post("/api/v1/auth/logout", headers=headers)

    assert response.status_code == 200, f"Status deveria ser 200, veio: {response.status_code}"
    assert "Successfully logged out" in response.text


@pytest.mark.asyncio
async def test_refresh_invalid_token(async_client, test_client_token):
    """
    Testa refresh de token usando um refresh_token inválido.
    Deve retornar 401 Unauthorized.
    """
    headers = {"Authorization": f"Bearer {test_client_token}"}

    invalid_refresh_token = "invalid.token.value"

    response = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": invalid_refresh_token},
        headers=headers
    )

    assert response.status_code == 401, f"Status deveria ser 401, veio: {response.status_code}"
    assert "Invalid" in response.text or "invalid" in response.text.lower()
