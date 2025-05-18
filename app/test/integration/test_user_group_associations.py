# app/test/integration/test_user_group_associations.py

# Para Rodar o Script:
# pytest app/test/integration/test_user_group_associations.py -v

# Testes de Associações Usuário-Grupo: Verificam a adição/remoção de usuários a grupos e a obtenção correta de permissões efetivas.

import pytest
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.application.use_cases.user_group_use_cases import AsyncUserGroupService
from app.application.use_cases.group_use_cases import AsyncGroupService
from app.application.dtos.group_dto import GroupCreate, UserGroupUpdate, GroupPermissionUpdate


@pytest.mark.asyncio
async def test_add_remove_user_to_groups(db_session: AsyncSession, create_test_user):
    """
    Testa adicionar e remover um usuário de grupos.
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
        email=f"group-test-user-{uuid.uuid4()}@example.com",
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(test_user)
    await db_session.commit()

    # Criar grupos de teste
    group_service = AsyncGroupService(db_session)
    group1 = await group_service.create_group(superuser, GroupCreate(name=f"test-group1-{uuid.uuid4()}"))
    group2 = await group_service.create_group(superuser, GroupCreate(name=f"test-group2-{uuid.uuid4()}"))

    # Inicializar serviço de usuário-grupo
    user_group_service = AsyncUserGroupService(db_session)

    # Adicionar usuário aos grupos
    add_data = UserGroupUpdate(group_ids=[group1.id, group2.id])
    updated_user = await user_group_service.add_user_to_groups(superuser, test_user.id, add_data)

    # Verificar se os grupos foram adicionados
    user_groups = await user_group_service.get_user_groups(superuser, test_user.id)

    assert len(user_groups) == 2
    group_ids = [g.id for g in user_groups]
    assert group1.id in group_ids
    assert group2.id in group_ids

    # Remover usuário de um grupo
    remove_data = UserGroupUpdate(group_ids=[group1.id])
    updated_user = await user_group_service.remove_user_from_groups(superuser, test_user.id, remove_data)

    # Verificar se o grupo foi removido
    user_groups = await user_group_service.get_user_groups(superuser, test_user.id)

    assert len(user_groups) == 1
    assert user_groups[0].id == group2.id


@pytest.mark.asyncio
async def test_user_effective_permissions(db_session: AsyncSession, create_test_user):
    """
    Testa obtenção das permissões efetivas de um usuário.
    """
    # Preparar superusuário
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Criar usuário de teste
    from app.adapters.outbound.security.auth_user_manager import UserAuthManager
    hashed_password = await UserAuthManager.hash_password("TestPassword123!")

    test_user = User(
        id=uuid.uuid4(),
        email=f"perm-test-user-{uuid.uuid4()}@example.com",
        password=hashed_password,
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow()
    )
    db_session.add(test_user)
    await db_session.commit()

    # Obter algumas permissões do banco
    stmt = select(AuthPermission).limit(3)
    result = await db_session.execute(stmt)
    permissions = result.scalars().all()

    # Criar grupo e atribuir algumas permissões
    group_service = AsyncGroupService(db_session)
    test_group = await group_service.create_group(superuser, GroupCreate(name=f"perm-group-{uuid.uuid4()}"))

    # Atribuir primeiras duas permissões ao grupo
    add_data = GroupPermissionUpdate(permission_ids=[permissions[0].id, permissions[1].id])
    await group_service.add_permissions_to_group(superuser, test_group.id, add_data)

    # Adicionar usuário ao grupo
    user_group_service = AsyncUserGroupService(db_session)
    group_data = UserGroupUpdate(group_ids=[test_group.id])
    await user_group_service.add_user_to_groups(superuser, test_user.id, group_data)

    # Adicionar terceira permissão diretamente ao usuário
    perm_data = [permissions[2].id]
    await user_group_service.add_direct_permissions_to_user(superuser, test_user.id, perm_data)

    # Obter permissões efetivas
    user_permissions = await user_group_service.get_user_permissions(superuser, test_user.id)

    # Verificar permissões
    assert len(user_permissions.group_permissions) > 0
    assert len(user_permissions.direct_permissions) > 0

    # Verificar se as permissões específicas estão presentes
    direct_perm_ids = [p.id for p in user_permissions.direct_permissions]
    assert permissions[2].id in direct_perm_ids

    # Verificar permissões efetivas (devem incluir todas)
    for perm in permissions:
        assert perm.codename in user_permissions.effective_permissions
