# app/test/unit/user_group/test_password_protection.py

# Para rodar o script
# pytest app/test/unit/user_group/test_password_protection.py -v

import re
import pytest
from uuid import uuid4
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.adapters.outbound.persistence.models.user_group.base_model import register_password_protection
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_password_protection_on_insert(db_session: AsyncSession):
    """
    Testa se o PasswordProtectionMiddleware impede que senhas em texto plano
    sejam salvas no banco de dados sem criptografia.
    """
    # Garante que os eventos estão registrados (caso rodando isolado)
    register_password_protection()

    plain_password = "SuperSecretPassword123!"
    user = User(
        id=uuid4(),
        email=f"securetest-{uuid4()}@example.com",
        password=plain_password,  # Texto puro
        is_active=True,
        is_superuser=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Verifica se a senha foi convertida para um hash bcrypt
    assert re.match(r'^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$', user.password), "Senha não foi protegida corretamente!"
    assert user.password != plain_password, "Senha foi salva em texto plano!"

@pytest.mark.asyncio
async def test_password_protection_on_update(db_session: AsyncSession):
    """
    Testa se o PasswordProtectionMiddleware também age durante atualizações (update).
    """
    register_password_protection()

    # Primeiro cria um usuário normalmente
    user = User(
        id=uuid4(),
        email=f"secureupdate-{uuid4()}@example.com",
        password="$2b$12$abcdefghijklmnopqrstuvwx1234567890abcdefgHIJKLMNOpq",  # Hash válido
        is_active=True,
        is_superuser=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Atualiza a senha para texto puro (o middleware deve interceptar)
    new_plain_password = "NewPlainPassword!"
    user.password = new_plain_password

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Verifica que a senha foi criptografada novamente
    assert re.match(r'^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$', user.password), "Senha de update não foi protegida corretamente!"
    assert user.password != new_plain_password, "Senha foi salva em texto plano após update!"
