# Import Base first
from app.adapters.outbound.persistence.models.base_model import Base

# Import association tables first
from app.adapters.outbound.persistence.models.user_access_group import user_access_groups
from app.adapters.outbound.persistence.models.user_access_permission import user_access_permission
from app.adapters.outbound.persistence.models.auth_group_permissions import auth_group_permissions

# Then import models that use those tables
from app.adapters.outbound.persistence.models.auth_content_type import AuthContentType
from app.adapters.outbound.persistence.models.auth_permission import AuthPermission
from app.adapters.outbound.persistence.models.auth_group import AuthGroup
from app.adapters.outbound.persistence.models.user_model import User
from app.adapters.outbound.persistence.models.client_model import Client

# # app/adapters/outbound/persistence/models/__init__.py
#
# """
# Módulo de modelos de dados.
#
# Este módulo exporta todos os modelos SQLAlchemy do sistema,
# facilitando a importação e uso em outros módulos.
# """
#
# # Importar Base
# from app.adapters.outbound.persistence.models.base_model import Base
#
# # Importar modelos principais
# from app.adapters.outbound.persistence.models.user_model import User, user_access_groups, user_access_permission
# from app.adapters.outbound.persistence.models.client_model import Client
#
# # Importar modelos de autorização
# from app.adapters.outbound.persistence.models.auth_group import AuthGroup
# from app.adapters.outbound.persistence.models.auth_permission import AuthPermission
# from app.adapters.outbound.persistence.models.auth_content_type import AuthContentType
# from app.adapters.outbound.persistence.models.auth_group_permissions import auth_group_permissions
#
# # Exportar todos os modelos
# __all__ = [
#     # Base
#     "Base",
#
#     # Modelos principais
#     "User",
#     "Client",
#
#     # Tabelas de associação
#     "user_access_groups",
#     "user_access_permission",
#     "auth_group_permissions",
#
#     # Modelos de autorização
#     "AuthGroup",
#     "AuthPermission",
#     "AuthContentType",
# ]
