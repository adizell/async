# app/domain/models/content_type.py

"""
Modelo de domínio para ContentType.

Define a entidade ContentType de forma pura, sem dependências
de frameworks de persistência ou infraestrutura.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Permission:
    """Representação de domínio para uma permissão."""
    id: int
    name: str
    codename: str
    content_type_id: int


@dataclass
class ContentType:
    """
    Modelo de domínio para tipos de conteúdo.

    Representa um tipo de entidade no sistema para o qual
    permissões podem ser definidas.
    """
    id: Optional[int]  # Optional para permitir criação sem ID
    app_label: str  # Domínio ou subsistema (ex: "user", "product")
    model: str  # Tipo de entidade (ex: "create", "read", "update")
    permissions: List[Permission] = None

    def __post_init__(self):
        """Inicializa coleções vazias se necessário."""
        if self.permissions is None:
            self.permissions = []

    def add_permission(self, permission: Permission) -> None:
        """
        Adiciona uma permissão a este tipo de conteúdo.

        Args:
            permission: A permissão a ser adicionada
        """
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission_id: int) -> None:
        """
        Remove uma permissão deste tipo de conteúdo.

        Args:
            permission_id: ID da permissão a ser removida
        """
        self.permissions = [p for p in self.permissions if p.id != permission_id]

    def has_permission(self, codename: str) -> bool:
        """
        Verifica se este tipo de conteúdo tem uma permissão específica.

        Args:
            codename: Código da permissão a verificar

        Returns:
            True se a permissão existir, False caso contrário
        """
        return any(p.codename == codename for p in self.permissions)

    def get_full_name(self) -> str:
        """
        Retorna o nome completo deste tipo de conteúdo no formato app_label.model.

        Returns:
            Nome completo do tipo de conteúdo
        """
        return f"{self.app_label}.{self.model}"
