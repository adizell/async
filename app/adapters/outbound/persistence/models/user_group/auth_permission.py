# app/adapters/outbound/persistence/models/user_group/auth_permission.py

"""
Modelo de persistência para Permission.

Este módulo define o modelo SQLAlchemy que representa permissões
no sistema, mapeando entre o domínio e o banco de dados.
"""

from sqlalchemy import BigInteger, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.adapters.outbound.persistence.models.user_group.base_model import Base
from app.domain.models.content_type import Permission as DomainPermission


class AuthPermission(Base):
    """
    Modelo SQLAlchemy para permissão no sistema de controle de acesso.

    Representa uma permissão específica que pode ser atribuída
    diretamente a um usuário ou a um grupo.

    Attributes:
        id: Identificador único da permissão
        name: Nome legível da permissão (ex: "Can list_species")
        codename: Código único que identifica a permissão (ex: "list_species")
        content_type_id: ID do tipo de conteúdo associado
        content_type: Relação com o tipo de conteúdo
        groups: Grupos que possuem esta permissão
    """
    __tablename__ = "auth_permission"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    codename: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    content_type_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth_content_type.id"), nullable=False)

    # Relações
    content_type = relationship("AuthContentType", back_populates="permissions", lazy="joined")
    groups = relationship("AuthGroup", secondary="auth_group_permissions", back_populates="permissions")

    def __repr__(self) -> str:
        """Representação em string do objeto AuthPermission."""
        return f"<AuthPermission(codename={self.codename})>"

    def to_domain(self) -> DomainPermission:
        """
        Converte o modelo de persistência para o modelo de domínio.

        Returns:
            Instância do modelo de domínio Permission
        """
        return DomainPermission(
            id=self.id,
            name=self.name,
            codename=self.codename,
            content_type_id=self.content_type_id
        )

    @classmethod
    def from_domain(cls, domain_permission: DomainPermission) -> 'AuthPermission':
        """
        Cria um modelo de persistência a partir do modelo de domínio.

        Args:
            domain_permission: Modelo de domínio Permission

        Returns:
            Instância do modelo de persistência AuthPermission
        """
        return cls(
            id=domain_permission.id if domain_permission.id else None,
            name=domain_permission.name,
            codename=domain_permission.codename,
            content_type_id=domain_permission.content_type_id
        )
