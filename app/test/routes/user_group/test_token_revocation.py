# app/test/routes/user_group/test_token_revocation.py

# Para Rodar o Script:
# pytest app/test/routes/user_group/test_token_revocation.py -v

import pytest
from sqlalchemy import select
from app.adapters.outbound.persistence.models.user_group.user_model import User


@pytest.mark.asyncio
async def test_token_revocation(async_client, db_session, test_client_token):
    """
    Testa que após o logout o token é revogado e não pode ser usado novamente.
    """
    # Dados do usuário de teste
    user_data = {
        "email": "test_user_token_revocation@example.com",  # Email único para evitar conflitos
        "password": "StrongP@ssword123"
    }

    client_headers = {"Authorization": f"Bearer {test_client_token}"}

    # Limpar usuário se já existir 
    stmt = select(User).where(User.email == user_data["email"])
    result = await db_session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        await db_session.delete(existing_user)
        await db_session.commit()

    # 1. Registrar usuário
    response_register = await async_client.post(
        "/api/v1/auth/register",
        json=user_data,
        headers=client_headers
    )
    assert response_register.status_code in (200, 201), f"Erro ao registrar usuário: {response_register.text}"

    # 2. Login para obter token
    response_login = await async_client.post(
        "/api/v1/auth/login",
        json=user_data,
        headers=client_headers
    )
    assert response_login.status_code == 200, f"Erro ao logar usuário: {response_login.text}"

    tokens = response_login.json()
    access_token = tokens["access_token"]
    user_headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Verificar que token funciona inicialmente
    response_me = await async_client.get(
        "/api/v1/user/me",
        headers=user_headers
    )
    assert response_me.status_code == 200, f"Token válido não funciona: {response_me.text}"

    # 4. Fazer logout (isto deve adicionar token à blacklist)
    response_logout = await async_client.post(
        "/api/v1/auth/logout",
        headers=user_headers
    )
    assert response_logout.status_code == 200, f"Erro ao fazer logout: {response_logout.text}"
    assert "logged out" in response_logout.json().get("detail", "").lower(), "Mensagem não confirma logout"

    # 5. Tentar usar token revogado - deve falhar com 401
    response_me_revoked = await async_client.get(
        "/api/v1/user/me",
        headers=user_headers
    )
    assert response_me_revoked.status_code == 401, "Token revogado ainda está sendo aceito!"
    assert "revoked" in response_me_revoked.text.lower() or "token" in response_me_revoked.text.lower(), \
        "Mensagem não indica token revogado"
