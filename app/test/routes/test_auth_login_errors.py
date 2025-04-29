# app/test/routes/test_auth_login_errors.py

# Para rodar o arquivo
# pytest app/test/routes/test_auth_login_errors.py -v

"""
Testes de autenticação: login com credenciais inválidas.

Este módulo testa se a API responde corretamente (401 Unauthorized)
ao tentar autenticar com email e/ou senha inválidos.
"""

import pytest


@pytest.mark.asyncio
async def test_login_with_nonexistent_user(async_client, test_client_token):
    """
    Testa login com credenciais válidas mas usuário inexistente.
    Deve retornar 401 Unauthorized e a mensagem 'Incorrect email or password'.
    """
    headers = {"Authorization": f"Bearer {test_client_token}"}

    # Dados de login válidos em formato, mas para usuário que não existe
    invalid_login_data = {
        "email": "userdoesnotexist@example.com",
        "password": "ValidP@ssword123"
    }

    response = await async_client.post("/api/v1/auth/login", json=invalid_login_data, headers=headers)

    assert response.status_code == 401, f"Deveria retornar 401 Unauthorized, retornou {response.status_code}."
    response_json = response.json()

    assert "detail" in response_json, "Resposta deveria conter o campo 'detail'."
    assert response_json[
               "detail"] == "Incorrect email or password", "Mensagem deveria ser 'Incorrect email or password'."
