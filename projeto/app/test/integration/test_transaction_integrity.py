# app/test/integration/test_transaction_integrity.py

# Para Rodar o Script:
# pytest app/test/integration/test_transaction_integrity.py -v

# Testes de Transações: Validam a integridade das transações, incluindo o rollback em caso de erro.

import pytest
import uuid
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.user_model import User


@pytest.mark.asyncio
async def test_transaction_rollback_on_error(db_session: AsyncSession):
    """
    Testa se o rollback da transação funciona corretamente em caso de erro.
    """
    # Preparar dados de teste
    user_id = uuid.uuid4()
    email = f"transaction-test-{uuid.uuid4()}@example.com"

    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    # Criar usuário inicial
    user = User(
        id=user_id,
        email=email,
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()

    # Tentar uma operação que vai falhar dentro de uma transação
    try:
        # Primeiro, fazer uma alteração válida
        update_stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
        )
        await db_session.execute(update_stmt)

        # Em seguida, uma operação que falha (duplicar um ID)
        duplicate_user = User(
            id=user_id,  # ID duplicado causa erro
            email=f"duplicate-{uuid.uuid4()}@example.com",
            password=hashed_password,
            is_active=True,
            is_superuser=False,
            created_at=datetime.utcnow()
        )
        db_session.add(duplicate_user)

        await db_session.commit()  # Isto deve falhar

        assert False, "Isso não deveria ser executado - a operação deveria falhar"

    except Exception:
        await db_session.rollback()

    # Verificar se o estado original foi mantido (rollback funcionou)
    stmt = select(User).where(User.id == user_id)
    result = await db_session.execute(stmt)
    fetched_user = result.scalars().unique().one()  # Add unique() here

    # O usuário deve ainda estar ativo, já que houve rollback da transação
    assert fetched_user.is_active == True, "A transação deveria ter feito rollback"


@pytest.mark.asyncio
async def test_transaction_commit_success(db_session: AsyncSession):
    """
    Testa se múltiplas operações são executadas corretamente em uma transação.
    """
    # Preparar dados de teste
    user1_id = uuid.uuid4()
    user2_id = uuid.uuid4()
    email1 = f"trans-test1-{uuid.uuid4()}@example.com"
    email2 = f"trans-test2-{uuid.uuid4()}@example.com"

    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    # Criar usuários em uma única transação
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
        is_superuser=True,
        created_at=datetime.utcnow()
    )

    db_session.add_all([user1, user2])
    await db_session.commit()

    # Verificar se ambos foram criados
    stmt = select(User).where(User.id.in_([user1_id, user2_id]))
    result = await db_session.execute(stmt)
    users = result.scalars().unique().all()  # Add unique() here

    assert len(users) == 2, "Ambos os usuários deveriam ter sido criados"

    # Agora atualizar e excluir na mesma transação
    update_stmt = (
        update(User)
        .where(User.id == user1_id)
        .values(email=f"updated-{email1}")
    )
    await db_session.execute(update_stmt)

    delete_stmt = delete(User).where(User.id == user2_id)
    await db_session.execute(delete_stmt)

    await db_session.commit()

    # Verificar se as operações foram aplicadas
    # Usuário 1 deve estar atualizado
    user1_stmt = select(User).where(User.id == user1_id)
    result = await db_session.execute(user1_stmt)
    updated_user1 = result.scalars().one()

    assert updated_user1.email == f"updated-{email1}", "O email deveria ter sido atualizado"

    # Usuário 2 deve ter sido excluído
    user2_stmt = select(User).where(User.id == user2_id)
    result = await db_session.execute(user2_stmt)
    deleted_user2 = result.scalars().one_or_none()
