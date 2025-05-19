# app/test/integration/test_group_permission_operations.py

# Para Rodar o Script:
# pytest app/test/integration/test_group_permission_operations.py -v

# Testes de Grupo e Permissões: Garantem que as associações entre grupos e permissões funcionem como esperado.

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.application.use_cases.group_use_cases import AsyncGroupService
from app.application.dtos.group_dto import GroupCreate, GroupUpdate, GroupPermissionUpdate
from app.domain.exceptions import ResourceAlreadyExistsException


@pytest.mark.asyncio
async def test_group_create_update_cycle(db_session: AsyncSession, create_test_user):
    """
    Testa o ciclo completo de criação e atualização de um grupo.
    """
    # Obter usuário com permissões
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Inicializar serviço
    service = AsyncGroupService(db_session)

    # Criar grupo
    group_name = f"test-group-{uuid.uuid4()}"
    group_data = GroupCreate(name=group_name)

    created_group = await service.create_group(superuser, group_data)

    # Verificar criação
    assert created_group.name == group_name
    assert isinstance(created_group.id, int)
    assert hasattr(created_group, "permissions")

    # Atualizar grupo
    new_name = f"updated-group-{uuid.uuid4()}"
    update_data = GroupUpdate(name=new_name)

    updated_group = await service.update_group(superuser, created_group.id, update_data)

    # Verificar atualização
    assert updated_group.id == created_group.id
    assert updated_group.name == new_name

    # Verificar diretamente no banco de dados
    stmt = select(AuthGroup).where(AuthGroup.id == created_group.id)
    result = await db_session.execute(stmt)
    db_group = result.scalars().unique().one()  # Add unique() here

    assert db_group.name == new_name


@pytest.mark.asyncio
async def test_group_duplicate_name(db_session: AsyncSession, create_test_user):
    """
    Testa tentativa de criar um grupo com nome duplicado.
    Deve falhar com ResourceAlreadyExistsException.
    """
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    service = AsyncGroupService(db_session)

    # Criar primeiro grupo
    group_name = f"duplicate-test-{uuid.uuid4()}"
    group_data = GroupCreate(name=group_name)

    await service.create_group(superuser, group_data)

    # Tentar criar segundo grupo com mesmo nome
    with pytest.raises(ResourceAlreadyExistsException):
        await service.create_group(superuser, group_data)


@pytest.mark.asyncio
async def test_add_and_remove_permissions_to_group(db_session: AsyncSession, create_test_user):
    """
    Testa adicionar e remover permissões de um grupo.
    """
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Inicializar serviços
    group_service = AsyncGroupService(db_session)

    # Criar grupo para teste
    group_data = GroupCreate(name=f"perm-test-group-{uuid.uuid4()}")
    group = await group_service.create_group(superuser, group_data)

    # Obter algumas permissões do banco
    stmt = select(AuthPermission).limit(2)
    result = await db_session.execute(stmt)
    permissions = result.scalars().all()

    assert len(permissions) > 0, "Precisa haver permissões no banco para este teste"

    permission_ids = [p.id for p in permissions]

    # Adicionar permissões ao grupo
    add_data = GroupPermissionUpdate(permission_ids=permission_ids)
    updated_group = await group_service.add_permissions_to_group(superuser, group.id, add_data)

    # Verificar se as permissões foram adicionadas
    assert len(updated_group.permissions) >= len(permission_ids)
    added_perm_ids = [p.id for p in updated_group.permissions]
    for pid in permission_ids:
        assert pid in added_perm_ids

    # Remover permissões
    remove_data = GroupPermissionUpdate(permission_ids=permission_ids)
    updated_group = await group_service.remove_permissions_from_group(superuser, group.id, remove_data)

    # Verificar se as permissões foram removidas
    remaining_perm_ids = [p.id for p in updated_group.permissions]
    for pid in permission_ids:
        assert pid not in remaining_perm_ids
