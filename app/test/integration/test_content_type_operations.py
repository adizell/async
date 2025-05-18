# app/test/integration/test_content_type_operations.py

# Para Rodar o Script:
# app/test/integration/test_content_type_operations.py -v

# Testes de Tipo de Conteúdo: Verificam o ciclo completo de CRUD para tipos de conteúdo.

import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.auth_content_type import AuthContentType
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.application.use_cases.content_type_use_cases import AsyncContentTypeService
from app.domain.exceptions import ResourceNotFoundException, ResourceAlreadyExistsException


@pytest.mark.asyncio
async def test_content_type_create_update_cycle(db_session: AsyncSession, create_test_user):
    """
    Testa o ciclo completo de criação, leitura e atualização de um tipo de conteúdo.
    """
    # Preparar superusuário
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Inicializar serviço
    service = AsyncContentTypeService(db_session)

    # 1. Criar tipo de conteúdo
    app_label = f"test-app-{uuid.uuid4().hex[:8]}"
    model = f"test-model-{uuid.uuid4().hex[:8]}"

    created_ct = await service.create_content_type(superuser, app_label, model)

    # Verificar criação
    assert created_ct.app_label == app_label
    assert created_ct.model == model
    assert created_ct.id is not None

    # 2. Verificar se pode ser encontrado pelo ID
    fetched_ct = await service.get_content_type(superuser, created_ct.id)

    assert fetched_ct.id == created_ct.id
    assert fetched_ct.app_label == app_label
    assert fetched_ct.model == model

    # 3. Atualizar tipo de conteúdo
    new_app_label = f"updated-app-{uuid.uuid4().hex[:8]}"
    new_model = f"updated-model-{uuid.uuid4().hex[:8]}"

    updated_ct = await service.update_content_type(
        superuser, created_ct.id, new_app_label, new_model
    )

    # Verificar atualização
    assert updated_ct.id == created_ct.id
    assert updated_ct.app_label == new_app_label
    assert updated_ct.model == new_model

    # Verificar diretamente no banco de dados
    stmt = select(AuthContentType).where(AuthContentType.id == created_ct.id)
    result = await db_session.execute(stmt)
    db_ct = result.scalars().one()

    assert db_ct.app_label == new_app_label
    assert db_ct.model == new_model


@pytest.mark.asyncio
async def test_content_type_duplicate(db_session: AsyncSession, create_test_user):
    """
    Testa tentativa de criar um tipo de conteúdo duplicado.
    Deve falhar com ResourceAlreadyExistsException.
    """
    # Preparar superusuário
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Inicializar serviço
    service = AsyncContentTypeService(db_session)

    # Criar tipo de conteúdo
    app_label = f"dup-app-{uuid.uuid4().hex[:8]}"
    model = f"dup-model-{uuid.uuid4().hex[:8]}"

    await service.create_content_type(superuser, app_label, model)

    # Tentar criar novamente com mesmo app_label e model
    with pytest.raises(ResourceAlreadyExistsException):
        await service.create_content_type(superuser, app_label, model)

    # Verificar também durante atualização
    # Criar outro tipo de conteúdo primeiro
    other_ct = await service.create_content_type(
        superuser,
        f"other-app-{uuid.uuid4().hex[:8]}",
        f"other-model-{uuid.uuid4().hex[:8]}"
    )

    # Tentar atualizar para o mesmo app_label/model que já existe
    with pytest.raises(ResourceAlreadyExistsException):
        await service.update_content_type(superuser, other_ct.id, app_label, model)


@pytest.mark.asyncio
async def test_content_type_delete(db_session: AsyncSession, create_test_user):
    """
    Testa exclusão de um tipo de conteúdo.
    """
    # Preparar superusuário
    superuser = create_test_user
    superuser.is_superuser = True
    await db_session.commit()

    # Inicializar serviço
    service = AsyncContentTypeService(db_session)

    # Criar tipo de conteúdo
    app_label = f"del-app-{uuid.uuid4().hex[:8]}"
    model = f"del-model-{uuid.uuid4().hex[:8]}"

    created_ct = await service.create_content_type(superuser, app_label, model)

    # Excluir tipo de conteúdo
    await service.delete_content_type(superuser, created_ct.id)

    # Verificar se foi excluído
    with pytest.raises(ResourceNotFoundException):
        await service.get_content_type(superuser, created_ct.id)

    # Verificar diretamente no banco
    stmt = select(AuthContentType).where(AuthContentType.id == created_ct.id)
    result = await db_session.execute(stmt)
    db_ct = result.scalars().one_or_none()

    assert db_ct is None, "O tipo de conteúdo deveria ter sido excluído do banco"
