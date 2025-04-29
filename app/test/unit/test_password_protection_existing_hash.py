# app/test/unit/test_password_protection_existing_hash.py

# Para rodar o script
# pytest app/test/unit/test_password_protection_existing_hash.py

import pytest
from app.shared.middleware.logging_middleware import PasswordProtectionMiddleware
from app.adapters.outbound.security.auth_user_manager import UserAuthManager


class DummyUser:
    def __init__(self, password):
        self.password = password


@pytest.mark.asyncio
async def test_password_protection_does_not_rehash_existing_hash():
    """
    Garante que senhas já criptografadas não sejam re-hashadas novamente.
    """
    # Criar um hash válido
    raw_password = "TestPassword123!"
    hashed_password = await UserAuthManager.hash_password(raw_password)

    # Simula objeto vindo do ORM já com hash
    user = DummyUser(password=hashed_password)

    # Guarda o hash original
    original_password = user.password

    # Executa o middleware
    PasswordProtectionMiddleware.before_insert_or_update(None, None, user)

    # A senha deve permanecer igual
    assert user.password == original_password, "Senha hashada foi alterada indevidamente!"


@pytest.mark.asyncio
async def test_password_protection_does_not_rehash_existing_bcrypt():
    """
    Garante que o PasswordProtectionMiddleware não re-hash uma senha já em formato bcrypt.
    """
    # Senha já no formato bcrypt
    existing_hashed_password = "$2b$12$KixZnS8O29p/DbLSmlDwQeZcdUVf0Z.yuRpN/UX5H1O3U8l6zvJ9W"
    user = DummyUser(password=existing_hashed_password)

    PasswordProtectionMiddleware.before_insert_or_update(None, None, user)

    # Senha deve permanecer inalterada
    assert user.password == existing_hashed_password
