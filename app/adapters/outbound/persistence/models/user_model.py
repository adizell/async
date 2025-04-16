# app/adapters/outbound/persistence/models/user_model.py

from sqlalchemy import (
    Column,
    Boolean,
    String,
    DateTime,
    func,
    Table,
    ForeignKey,
    BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.adapters.outbound.persistence.models.base_model import Base
from app.adapters.outbound.persistence.models.user_access_group import user_access_groups

# Associação many-to-many entre usuários e grupos
# aud_user_access_groups = Table(
#     "user_access_groups",
#     Base.metadata,
#     Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
#     Column("group_id", BigInteger, ForeignKey("auth_group.id", ondelete="CASCADE"), primary_key=True),
# )

# Associação many-to-many entre usuários e permissões diretas
user_access_permission = Table(
    "user_access_permission",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", BigInteger, ForeignKey("auth_permission.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relações
    groups = relationship(
        "AuthGroup",
        secondary=user_access_groups,
        back_populates="users",
        lazy="joined"
    )
    permissions = relationship(
        "AuthPermission",
        secondary=user_access_permission,
        back_populates="users",
        lazy="joined"
    )
    # Tokens de refresh
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User(email={self.email}, active={self.is_active})>"

    def has_permission(self, permission_codename: str) -> bool:
        if self.is_superuser:
            return True
        if any(perm.codename == permission_codename for perm in self.permissions):
            return True
        for group in self.groups:
            if any(perm.codename == permission_codename for perm in group.permissions):
                return True
        return False


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_revoked = Column(Boolean, default=False)

    # Relação com usuário
    user = relationship(
        "User",
        back_populates="refresh_tokens"
    )
