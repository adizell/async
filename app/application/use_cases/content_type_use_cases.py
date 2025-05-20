# app/application/use_cases/content_type_use_cases.py

"""
Casos de uso relacionados a tipos de conteúdo.

Este módulo implementa os casos de uso para gerenciamento de
tipos de conteúdo no sistema de permissões.
"""

import logging
from typing import List, Optional
from fastapi_pagination import Params, Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.outbound.persistence.models.user_group.auth_content_type import AuthContentType
from app.adapters.outbound.persistence.models.user_group.user_model import User
from app.adapters.outbound.persistence.repositories.content_type_repository import content_type_repository
from app.domain.models.content_type import ContentType
from app.domain.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    PermissionDeniedException
)

logger = logging.getLogger(__name__)


class AsyncContentTypeService:
    """
    Serviço para gerenciamento de tipos de conteúdo no sistema de permissões.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def list_content_types(
            self, current_user: User, params: Params
    ) -> Page:
        """
        Lista todos os tipos de conteúdo com paginação.

        Args:
            current_user: Usuário autenticado
            params: Parâmetros de paginação

        Returns:
            Página de tipos de conteúdo

        Raises:
            PermissionDeniedException: Se o usuário não tiver permissão
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} attempted to list content types without permission")
            raise PermissionDeniedException("You don't have permission to view content types")

        # Para paginação com fastapi_pagination, usamos o modelo de persistência diretamente
        stmt = (
            select(AuthContentType)
            .order_by(AuthContentType.app_label, AuthContentType.model)
        )

        return await paginate(self.db, stmt, params)

    async def get_content_type(
            self, current_user: User, content_type_id: int
    ) -> ContentType:
        """
        Obtém um tipo de conteúdo específico por ID.

        Args:
            current_user: Usuário autenticado
            content_type_id: ID do tipo de conteúdo

        Returns:
            Tipo de conteúdo

        Raises:
            PermissionDeniedException: Se o usuário não tiver permissão
            ResourceNotFoundException: Se o tipo de conteúdo não for encontrado
        """
        if not current_user.is_superuser and not current_user.has_permission("view_permissions"):
            logger.warning(f"User {current_user.email} attempted to view content type details without permission")
            raise PermissionDeniedException("You don't have permission to view content type details")

        return await content_type_repository.get_by_id(self.db, content_type_id)

    async def create_content_type(
            self, current_user: User, app_label: str, model: str
    ) -> ContentType:
        """
        Cria um novo tipo de conteúdo.

        Args:
            current_user: Usuário autenticado
            app_label: Nome da aplicação/domínio
            model: Nome do modelo/entidade

        Returns:
            Tipo de conteúdo criado

        Raises:
            PermissionDeniedException: Se o usuário não tiver permissão
            ResourceAlreadyExistsException: Se o tipo de conteúdo já existir
        """
        if not current_user.is_superuser and not current_user.has_permission("manage_permissions"):
            logger.warning(f"User {current_user.email} attempted to create content type without permission")
            raise PermissionDeniedException("You don't have permission to create content types")

        # Verificar se já existe
        existing_content_type = await content_type_repository.get_by_app_label_and_model(
            self.db, app_label, model
        )

        if existing_content_type:
            raise ResourceAlreadyExistsException(
                detail=f"Content type with app_label '{app_label}' and model '{model}' already exists"
            )

        # Criar novo tipo de conteúdo
        new_content_type = ContentType(
            id=None,  # Será atribuído pelo banco
            app_label=app_label,
            model=model
        )

        return await content_type_repository.create(self.db, new_content_type)

    async def update_content_type(
            self, current_user: User, content_type_id: int, app_label: str, model: str
    ) -> ContentType:
        """
        Atualiza um tipo de conteúdo existente.

        Args:
            current_user: Usuário autenticado
            content_type_id: ID do tipo de conteúdo
            app_label: Novo nome da aplicação/domínio
            model: Novo nome do modelo/entidade

        Returns:
            Tipo de conteúdo atualizado

        Raises:
            PermissionDeniedException: Se o usuário não tiver permissão
            ResourceNotFoundException: Se o tipo de conteúdo não for encontrado
            ResourceAlreadyExistsException: Se outro tipo com mesmo app_label e model já existir
        """
        # Verificar permissão
        if not current_user.is_superuser and not current_user.has_permission("manage_permissions"):
            logger.warning(f"User {current_user.email} attempted to update content type without permission")
            raise PermissionDeniedException("You don't have permission to update content types")

        # Obter objeto existente
        current_content_type = await content_type_repository.get_by_id(self.db, content_type_id)

        # Verificar duplicação
        if (current_content_type.app_label != app_label or current_content_type.model != model):
            existing_content_type = await content_type_repository.get_by_app_label_and_model(
                self.db, app_label, model
            )

            if existing_content_type:
                raise ResourceAlreadyExistsException(
                    detail=f"Content type with app_label '{app_label}' and model '{model}' already exists"
                )

        # Atualizar os atributos no objeto de domínio existente
        current_content_type.app_label = app_label
        current_content_type.model = model

        # Passar o objeto existente atualizado
        return await content_type_repository.update(self.db, content_type_id, current_content_type)

    async def delete_content_type(
            self, current_user: User, content_type_id: int
    ) -> None:
        """
        Remove um tipo de conteúdo.

        Args:
            current_user: Usuário autenticado
            content_type_id: ID do tipo de conteúdo

        Raises:
            PermissionDeniedException: Se o usuário não tiver permissão
            ResourceNotFoundException: Se o tipo de conteúdo não for encontrado
        """
        if not current_user.is_superuser:
            logger.warning(f"User {current_user.email} attempted to delete content type without being a superuser")
            raise PermissionDeniedException("Only superusers can delete content types")

        await content_type_repository.delete(self.db, content_type_id)
