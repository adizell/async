# app/test/integration/test_user_update_operations.py

# Para Rodar o Script:
# pytest app/test/integration/test_user_update_operations.py -v

# Testes de Atualização de Usuário: Verificam se as atualizações de usuários são realizadas corretamente, mantendo IDs e validando campos únicos.

import pytest
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.use_cases.user_use_cases import AsyncUserService
from app.application.dtos.user_dto import UserUpdate, UserSelfUpdate
from app.domain.exceptions import ResourceNotFoundException, ResourceAlreadyExistsException


@pytest.mark.asyncio
async def test_user_self_update_success(db_session: AsyncSession):
    """
    Testa atualização do próprio usuário com sucesso.
    Verifica se a operação de atualização mantém o mesmo ID.
    """
    # Criar usuário para teste
    user_id = uuid.uuid4()
    original_email = f"user-self-update-{uuid.uuid4()}@example.com"
    new_email = f"updated-self-{uuid.uuid4()}@example.com"

    # Criar usuário no banco
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    user = User(
        id=user_id,
        email=original_email,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()

    # Inicializar serviço e DTO de atualização
    service = AsyncUserService(db_session)
    update_data = UserSelfUpdate(
        email=new_email,
        current_password="TestPassword123!",
        password="NewPassword456!"
    )

    # Executar a atualização
    updated_user = await service.update_self(user_id, update_data)

    # Verificar se o usuário foi atualizado corretamente
    assert updated_user.id == user_id, "O ID do usuário não deve mudar após atualização"
    assert updated_user.email == new_email, "O email deve ser atualizado"

    # Verificar se a senha foi alterada verificando se a senha antiga não funciona mais
    assert not await UserAuthManager.verify_password("TestPassword123!", updated_user.password)

    # Verificar se a nova senha funciona
    assert await UserAuthManager.verify_password("NewPassword456!", updated_user.password)

    # Verificar diretamente no banco de dados
    stmt = select(User).where(User.id == user_id)
    result = await db_session.execute(stmt)
    db_user = result.scalars().unique().one()  # Add unique()

    assert db_user.email == new_email, "Alteração do email deve ser persistida no banco"


@pytest.mark.asyncio
async def test_user_self_update_duplicate_email(db_session: AsyncSession):
    """
    Testa tentativa de atualização para um email já existente.
    Deve falhar com ResourceAlreadyExistsException.
    """
    # Criar dois usuários para teste
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()

    email1 = f"user1-{uuid.uuid4()}@example.com"
    email2 = f"user2-{uuid.uuid4()}@example.com"

    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    # Criar usuário 1
    user1 = User(
        id=user1_id,
        email=email1,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )

    # Criar usuário 2
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

    # Inicializar serviço e tentar atualizar user2 para ter o mesmo email que user1
    service = AsyncUserService(db_session)
    update_data = UserSelfUpdate(
        email=email1,
        current_password="TestPassword123!"
    )

    # Verificar se a exceção é lançada
    with pytest.raises(ResourceAlreadyExistsException):
        await service.update_self(user2_id, update_data)


@pytest.mark.asyncio
async def test_user_admin_update_multiple_fields(db_session: AsyncSession):
    """
    Testa atualização administrativa de múltiplos campos de um usuário.
    """
    # Criar usuário para teste
    user_id = uuid.uuid4()
    original_email = f"admin-update-{uuid.uuid4()}@example.com"
    new_email = f"updated-admin-{uuid.uuid4()}@example.com"

    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    user = User(
        id=user_id,
        email=original_email,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()

    # Inicializar serviço e DTO de atualização administrativa
    service = AsyncUserService(db_session)
    update_data = UserUpdate(
        email=new_email,
        password="AdminSet987!",
        is_active=False,
        is_superuser=True
    )

    # Executar a atualização
    updated_user = await service.update_user(user_id, update_data)

    # Verificar se todos os campos foram atualizados corretamente
    assert updated_user.id == user_id, "O ID do usuário não deve mudar"
    assert updated_user.email == new_email, "O email deve ser atualizado"
    assert await UserAuthManager.verify_password("AdminSet987!", updated_user.password), "A senha deve ser atualizada"
    assert updated_user.is_active == False, "O status ativo deve ser atualizado"
    assert updated_user.is_superuser == True, "O status de superusuário deve ser atualizado"

    # Verificar diretamente no banco de dados
    stmt = select(User).where(User.id == user_id)
    result = await db_session.execute(stmt)
    db_user = result.scalars().unique().one()  # Add unique()

    assert db_user.email == new_email
    assert db_user.is_active == False
    assert db_user.is_superuser == True


@pytest.mark.asyncio
async def test_user_update_nonexistent(db_session: AsyncSession):
    """
    Testa atualização de um usuário que não existe.
    Deve falhar com ResourceNotFoundException.
    """
    random_id = uuid.uuid4()

    service = AsyncUserService(db_session)
    update_data = UserUpdate(
        email="nonexistent@example.com",
        is_active=True
    )

    # Verificar se a exceção é lançada
    with pytest.raises(ResourceNotFoundException):
        await service.update_user(random_id, update_data)
