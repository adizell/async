# app/application/ports/outbound.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.models.user_domain_model import User
from app.domain.models.client_domain_model import Client


class UserRepositoryPort(ABC):
    """Repository interface for user operations"""

    @abstractmethod
    async def create(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID"""
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email"""
        pass

    @abstractmethod
    async def update(self, user_id: UUID, data: Dict[str, Any]) -> User:
        """Update a user"""
        pass

    @abstractmethod
    async def deactivate(self, user_id: UUID) -> None:
        """Deactivate a user"""
        pass

    @abstractmethod
    async def reactivate(self, user_id: UUID) -> None:
        """Reactivate a user"""
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """Delete a user permanently"""
        pass

    @abstractmethod
    async def list_users(self, skip: int, limit: int, order: str) -> List[User]:
        """List users with pagination"""
        pass


class TokenServicePort(ABC):
    """Service interface for token operations"""

    @abstractmethod
    async def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
        """Create an access token"""
        pass

    @abstractmethod
    async def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a refresh token"""
        pass

    @abstractmethod
    async def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify a token and return its payload"""
        pass
