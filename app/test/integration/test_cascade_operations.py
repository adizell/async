# app/test/integration/test_cascade_operations.py

# Para Rodar o Script:
# pytest app/test/integration/test_cascade_operations.py -v

# Testes de Cascata: Validam o comportamento de exclusão em cascata nas associações.

import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.user_model import User, user_access_groups
from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.application.use_cases.group_use_cases import AsyncGroupService
from app.application.use_cases.user_group_use_cases import AsyncUserGroupService
from app.application.dtos.group_dto import GroupCreate, UserGroupUpdate
from app.domain.exceptions import ResourceNotFoundException
from app.shared.utils.datetime_utils import DateTimeUtil  # Import our utility


@pytest.mark.asyncio
async def test_delete_group_cascade(db_session: AsyncSession, create_test_user):
    """
    Testa se a exclusão de um grupo cascateia corretamente para as associações.
    """
    # Preparar usuários
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Criar usuário de teste
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    test_user = User(
        id=uuid.uuid4(),
        email=f"cascade-test-user-{uuid.uuid4()}@example.com",
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=DateTimeUtil.utcnow_naive()  # Use our utility
    )
    db_session.add(test_user)
    await db_session.commit()

    # Criar grupo de teste
    group_service = AsyncGroupService(db_session)
    group = await group_service.create_group(
        superuser,
        GroupCreate(name=f"cascade-test-group-{uuid.uuid4()}")
    )

    # Associar usuário ao grupo
    user_group_service = AsyncUserGroupService(db_session)
    group_data = UserGroupUpdate(group_ids=[group.id])
    await user_group_service.add_user_to_groups(superuser, test_user.id, group_data)

    # Verificar se a associação foi criada
    check_stmt = select(user_access_groups).where(
        (user_access_groups.c.user_id == test_user.id) &
        (user_access_groups.c.group_id == group.id)
    )
    result = await db_session.execute(check_stmt)
    association = result.one_or_none()

    assert association is not None, "A associação deveria existir"

    # Excluir o grupo
    await group_service.delete_group(superuser, group.id)

    # Verificar se o grupo foi excluído
    with pytest.raises(ResourceNotFoundException):
        await group_service.get_group(group.id)

    # Verificar se a associação também foi excluída (cascata)
    check_stmt = select(user_access_groups).where(
        (user_access_groups.c.user_id == test_user.id) &
        (user_access_groups.c.group_id == group.id)
    )
    result = await db_session.execute(check_stmt)
    association = result.one_or_none()

    assert association is None, "A associação deveria ter sido excluída em cascata"

    # Verificar se o usuário ainda existe
    user_stmt = select(User).where(User.id == test_user.id)
    result = await db_session.execute(user_stmt)
    user = result.scalars().one_or_none()

    assert user is not None, "O usuário não deveria ser excluído"


@pytest.mark.asyncio
async def test_delete_user_cascade(db_session: AsyncSession, create_test_user):
    """
    Testa se a exclusão de um usuário cascateia corretamente para as associações.
    """
    # Preparar usuários
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Criar usuário de teste
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    test_user = User(
        id=uuid.uuid4(),
        email=f"user-cascade-test-{uuid.uuid4()}@example.com",
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=DateTimeUtil.utcnow_naive()  # Use our utility
    )
    db_session.add(test_user)
    await db_session.commit()

    # Criar grupos de teste
    group_service = AsyncGroupService(db_session)
    group1 = await group_service.create_group(
        superuser,
        GroupCreate(name=f"user-cascade-group1-{uuid.uuid4()}")
    )
    group2 = await group_service.create_group(
        superuser,
        GroupCreate(name=f"user-cascade-group2-{uuid.uuid4()}")
    )

    # Associar usuário aos grupos
    user_group_service = AsyncUserGroupService(db_session)
    group_data = UserGroupUpdate(group_ids=[group1.id, group2.id])
    await user_group_service.add_user_to_groups(superuser, test_user.id, group_data)

    # Verificar se as associações foram criadas
    check_stmt = select(user_access_groups).where(user_access_groups.c.user_id == test_user.id)
    result = await db_session.execute(check_stmt)
    associations = result.all()

    assert len(associations) == 2, "Deveriam existir duas associações"

    # Excluir o usuário diretamente
    await db_session.delete(test_user)
    await db_session.commit()

    # Verificar se as associações foram excluídas (cascata)
    check_stmt = select(user_access_groups).where(user_access_groups.c.user_id == test_user.id)
    result = await db_session.execute(check_stmt)
    associations = result.all()

    assert len(associations) == 0, "As associações deveriam ter sido excluídas em cascata"

    # Verificar se os grupos ainda existem
    group_stmt = select(AuthGroup).where(AuthGroup.id.in_([group1.id, group2.id]))
    result = await db_session.execute(group_stmt)
    groups = result.scalars().all()

    assert len(groups) == 2, "Os grupos não deveriam ser excluídos"
