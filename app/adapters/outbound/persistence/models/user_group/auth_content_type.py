# app/adapters/outbound/persistence/models/user_group/auth_content_type.py

"""
Modelo de persistência para ContentType.

Este módulo define o modelo SQLAlchemy que representa tipos de conteúdo
para o sistema de permissões, mapeando entre o domínio e o banco de dados.
"""

from sqlalchemy import Column, BigInteger, String, Index
from sqlalchemy.orm import relationship
from app.adapters.outbound.persistence.models.user_group.base_model import Base
from app.domain.models.content_type import ContentType as DomainContentType
from app.domain.models.content_type import Permission as DomainPermission


class AuthContentType(Base):
    """
    Modelo SQLAlchemy para tipo de conteúdo no sistema de permissões.

    Representa uma categoria ou tipo de conteúdo ao qual permissões
    podem ser associadas, como 'user', 'pet', 'specie', etc.

    Attributes:
        id: Identificador único do tipo de conteúdo
        app_label: Nome da aplicação/domínio (ex: pet, specie, user)
        model: Nome da ação/entidade (ex: create, list, update)
        permissions: Relação com as permissões associadas a este tipo
    """
    __tablename__ = "auth_content_type"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    app_label = Column(String(100), nullable=False, index=True,
                       doc="Nome da aplicação ou domínio (ex: pet, specie)")
    model = Column(String(100), nullable=False, index=True,
                   doc="Ação ou entidade (ex: create, list, update)")

    # Relação com permissões
    permissions = relationship("AuthPermission", back_populates="content_type", cascade="all, delete-orphan")

    # Índice composto para app_label e model
    __table_args__ = (
        Index("idx_content_type_app_model", "app_label", "model"),
    )

    def __repr__(self) -> str:
        """Representação em string do objeto AuthContentType."""
        return f"<AuthContentType(app_label='{self.app_label}', model='{self.model}')>"

    def to_domain(self) -> DomainContentType:
        """
        Converte o modelo de persistência para o modelo de domínio.

        Returns:
            Instância do modelo de domínio ContentType
        """
        domain_permissions = [
            DomainPermission(
                id=perm.id,
                name=perm.name,
                codename=perm.codename,
                content_type_id=perm.content_type_id
            )
            for perm in self.permissions
        ]

        return DomainContentType(
            id=self.id,
            app_label=self.app_label,
            model=self.model,
            permissions=domain_permissions
        )

    @classmethod
    def from_domain(cls, domain_content_type: DomainContentType) -> 'AuthContentType':
        """
        Cria um modelo de persistência a partir do modelo de domínio.

        Args:
            domain_content_type: Modelo de domínio ContentType

        Returns:
            Instância do modelo de persistência AuthContentType
        """
        return cls(
            id=domain_content_type.id,
            app_label=domain_content_type.app_label,
            model=domain_content_type.model
        )
        # Nota: as permissões são geralmente gerenciadas separadamente
