# app/adapters/outbound/persistence/models/__init__.py

"""
Módulo de modelos de dados.

Este módulo exporta todos os modelos SQLAlchemy do sistema,
facilitando a importação e uso em outros módulos.
"""

# Importar Base
from app.adapters.outbound.persistence.models.user_group.base_model import Base

# Importar modelos principais
from app.adapters.outbound.persistence.models.user_group.user_model import User, user_access_groups, user_access_permission
from app.adapters.outbound.persistence.models.user_group.client_model import Client

# Importar modelos de autorização
from app.adapters.outbound.persistence.models.user_group.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_group.auth_permission import AuthPermission
from app.adapters.outbound.persistence.models.user_group.auth_content_type import AuthContentType
from app.adapters.outbound.persistence.models.user_group.auth_group_permissions import auth_group_permissions
from app.adapters.outbound.persistence.models.user_group.token_blacklist_model import TokenBlacklist

# Exportar todos os modelos
__all__ = [
    # Base
    "Base",

    # Modelos principais
    "User",
    "Client",

    # Tabelas de associação
    "user_access_groups",
    "user_access_permission",
    "auth_group_permissions",

    # Modelos de autorização
    "AuthGroup",
    "AuthPermission",
    "AuthContentType",
]
