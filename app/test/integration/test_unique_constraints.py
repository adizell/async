# app/test/integration/test_unique_constraints.py

# Para Rodar o Script:
# pytest app/test/integration/test_unique_constraints.py -v

# Testes de Restrições Únicas: Garantem que as validações de campos únicos funcionem corretamente na criação e atualização.

import pytest
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.use_cases.user_use_cases import AsyncUserService
from app.application.use_cases.auth_use_cases import AsyncAuthService
from app.application.dtos.user_dto import UserCreate, UserUpdate, UserSelfUpdate
from app.domain.exceptions import ResourceAlreadyExistsException


@pytest.mark.asyncio
async def test_unique_email_on_create(db_session: AsyncSession):
    """
    Testa se a validação de email único funciona corretamente na criação.
    """
    # Criar um serviço de autenticação
    auth_service = AsyncAuthService(db_session)

    # Criar primeiro usuário
    unique_email = f"unique-create-{uuid.uuid4()}@example.com"
    user_data = UserCreate(
        email=unique_email,
        password="Strong123Password!"
    )

    user1 = await auth_service.register_user(user_data)
    assert user1.email == unique_email

    # Tentar criar outro usuário com o mesmo email
    duplicate_data = UserCreate(
        email=unique_email,  # Mesmo email
        password="DifferentPass321!"
    )

    with pytest.raises(ResourceAlreadyExistsException):
        await auth_service.register_user(duplicate_data)


@pytest.mark.asyncio
async def test_unique_email_on_update_self(db_session: AsyncSession):
    """
    Testa se a validação de email único funciona corretamente na atualização pelo próprio usuário.
    """
    # Criar dois usuários
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()

    email1 = f"unique-update1-{uuid.uuid4()}@example.com"
    email2 = f"unique-update2-{uuid.uuid4()}@example.com"

    user1 = User(
        id=user1_id,
        email=email1,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )

    user2 = User(
        id=user2_id,
        email=email2,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )

    db_session.add_all([user1, user2])
    await db_session.commit()

    # Tentar atualizar user2 para ter o mesmo email que user1
    service = AsyncUserService(db_session)
    update_data = UserSelfUpdate(
        email=email1,
        current_password="TestPassword123!"
    )

    with pytest.raises(ResourceAlreadyExistsException):
        await service.update_self(user2_id, update_data)


@pytest.mark.asyncio
async def test_unique_email_on_admin_update(db_session: AsyncSession):
    """
    Testa se a validação de email único funciona corretamente na atualização administrativa.
    """
    # Criar dois usuários
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()

    email1 = f"unique-admin1-{uuid.uuid4()}@example.com"
    email2 = f"unique-admin2-{uuid.uuid4()}@example.com"

    user1 = User(
        id=user1_id,
        email=email1,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )

    user2 = User(
        id=user2_id,
        email=email2,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )

    db_session.add_all([user1, user2])
    await db_session.commit()

    # Tentar atualizar user2 para ter o mesmo email que user1
    service = AsyncUserService(db_session)
    update_data = UserUpdate(
        email=email1
    )

    with pytest.raises(ResourceAlreadyExistsException):
        await service.update_user(user2_id, update_data)
