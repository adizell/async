# app/adapters/outbound/persistence/repositories/content_type_repository.py

"""
Repositório para operações com ContentType.

Este módulo implementa o padrão Repository para isolar o domínio
das operações específicas de banco de dados para ContentType.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.outbound.persistence.models.user_group.auth_content_type import AuthContentType
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.domain.models.content_type import ContentType as DomainContentType, Permission as DomainPermission, ContentType
from app.domain.exceptions import ResourceNotFoundException, DatabaseOperationException


class ContentTypeRepository:
    """
    Repositório para operações com ContentType.
    Implementa acesso a dados isolando o domínio dos detalhes de persistência.
    """

    @staticmethod
    async def get_by_id(db: AsyncSession, content_type_id: int) -> DomainContentType:
        """
        Busca um ContentType pelo ID.

        Args:
            db: Sessão de banco de dados
            content_type_id: ID do tipo de conteúdo

        Returns:
            ContentType do domínio

        Raises:
            ResourceNotFoundException: Se o tipo de conteúdo não for encontrado
        """
        try:
            stmt = (
                select(AuthContentType)
                .options(selectinload(AuthContentType.permissions))
                .where(AuthContentType.id == content_type_id)
            )
            result = await db.execute(stmt)
            content_type = result.scalars().one_or_none()

            if not content_type:
                raise ResourceNotFoundException(
                    message=f"Content type with ID {content_type_id} not found",
                    resource_id=content_type_id
                )

            return content_type.to_domain()

        except ResourceNotFoundException:
            raise
        except Exception as e:
            raise DatabaseOperationException(
                message=f"Error retrieving content type with ID {content_type_id}",
                original_error=e
            )

    @staticmethod
    async def get_all(
            db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[DomainContentType]:
        """
        Lista todos os tipos de conteúdo com paginação.

        Args:
            db: Sessão de banco de dados
            skip: Número de registros para pular
            limit: Número máximo de registros a retornar

        Returns:
            Lista de objetos ContentType do domínio
        """
        try:
            stmt = (
                select(AuthContentType)
                .options(selectinload(AuthContentType.permissions))
                .order_by(AuthContentType.app_label, AuthContentType.model)
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            content_types = result.scalars().all()

            return [ct.to_domain() for ct in content_types]

        except Exception as e:
            raise DatabaseOperationException(
                message="Error retrieving content types",
                original_error=e
            )

    @staticmethod
    async def get_by_app_label_and_model(
            db: AsyncSession, app_label: str, model: str
    ) -> Optional[DomainContentType]:
        """
        Busca um ContentType pelo app_label e model.

        Args:
            db: Sessão de banco de dados
            app_label: Label da aplicação/domínio
            model: Nome do modelo/entidade

        Returns:
            ContentType do domínio ou None se não encontrado
        """
        try:
            stmt = (
                select(AuthContentType)
                .options(selectinload(AuthContentType.permissions))
                .where(
                    (AuthContentType.app_label == app_label) &
                    (AuthContentType.model == model)
                )
            )
            result = await db.execute(stmt)
            content_type = result.scalars().one_or_none()

            if not content_type:
                return None

            return content_type.to_domain()

        except Exception as e:
            raise DatabaseOperationException(
                message=f"Error retrieving content type ({app_label}.{model})",
                original_error=e
            )

    @staticmethod
    async def create(
            db: AsyncSession, domain_content_type: DomainContentType
    ) -> DomainContentType:
        """
        Cria um novo ContentType.

        Args:
            db: Sessão de banco de dados
            domain_content_type: Objeto ContentType do domínio

        Returns:
            ContentType do domínio com ID atribuído
        """
        try:
            content_type = AuthContentType.from_domain(domain_content_type)
            db.add(content_type)
            await db.flush()

            # Criar uma instância limpa para retornar, evitando lazy loading
            new_content_type = ContentType(
                id=content_type.id,
                app_label=content_type.app_label,
                model=content_type.model,
                permissions=[]  # Inicializar vazio para evitar lazy loading
            )

            return new_content_type

        except Exception as e:
            await db.rollback()
            raise DatabaseOperationException(
                message="Error creating content type",
                original_error=e
            )

    @staticmethod
    async def update(
            db: AsyncSession, content_type_id: int, domain_content_type: ContentType
    ) -> ContentType:
        """
        Atualiza um ContentType existente.

        Args:
            db: Sessão de banco de dados
            content_type_id: ID do tipo de conteúdo a atualizar
            domain_content_type: Objeto ContentType do domínio com novos valores

        Returns:
            ContentType atualizado

        Raises:
            ResourceNotFoundException: Se o tipo de conteúdo não for encontrado
            DatabaseOperationException: Em caso de erro no banco de dados
        """
        try:
            # Obter o registro existente
            stmt = select(AuthContentType).where(AuthContentType.id == content_type_id)
            result = await db.execute(stmt)
            content_type = result.scalars().one_or_none()

            if not content_type:
                raise ResourceNotFoundException(
                    message=f"Content type with ID {content_type_id} not found",
                    resource_id=content_type_id
                )

            # Atualizar atributos do objeto existente
            content_type.app_label = domain_content_type.app_label
            content_type.model = domain_content_type.model

            # Persistir alterações
            await db.flush()
            await db.refresh(content_type)

            # Retornar objeto de domínio atualizado
            return content_type.to_domain()

        except ResourceNotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseOperationException(
                message=f"Error updating content type with ID {content_type_id}",
                original_error=e
            )

    @staticmethod
    async def delete(db: AsyncSession, content_type_id: int) -> None:
        """
        Remove um ContentType.

        Args:
            db: Sessão de banco de dados
            content_type_id: ID do tipo de conteúdo a remover

        Raises:
            ResourceNotFoundException: Se o tipo de conteúdo não for encontrado
        """
        try:
            stmt = select(AuthContentType).where(AuthContentType.id == content_type_id)
            result = await db.execute(stmt)
            content_type = result.scalars().one_or_none()

            if not content_type:
                raise ResourceNotFoundException(
                    message=f"Content type with ID {content_type_id} not found",
                    resource_id=content_type_id
                )

            await db.delete(content_type)
            await db.flush()

        except ResourceNotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            raise DatabaseOperationException(
                message=f"Error deleting content type with ID {content_type_id}",
                original_error=e
            )


# Singleton para acesso global
content_type_repository = ContentTypeRepository()
