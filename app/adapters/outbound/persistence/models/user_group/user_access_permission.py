# app/adapters/outbound/persistence/models/user_access_permission.py

from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import BigInteger
from app.adapters.outbound.persistence.models.user_group.base_model import Base

########################################################################
# Tabela de associação many-to-many entre usuários e permissões

# A tabela user_access_permission é usada quando:
# 1.Um usuário precisa de permissões específicas sem pertencer a um grupo inteiro
# 2.Um usuário precisa de permissões temporárias para uma tarefa específica
# 3.Você quer dar permissões muito granulares a um usuário sem afetar outros
########################################################################

user_access_permission = Table(
    "user_access_permission",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("auth_permission.id", ondelete="CASCADE"), primary_key=True),
)
