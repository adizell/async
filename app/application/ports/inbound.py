# app/application/ports/inbound.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.models.user_domain_model import User
from app.domain.models.client_domain_model import Client


class UserInputPort(ABC):
    """Input port interface for user operations"""

    @abstractmethod
    async def register_user(self, user_data: Dict[str, Any]) -> User:
        """Register a new user"""
        pass

    @abstractmethod
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate a user and return tokens"""
        pass

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token using a refresh token"""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: UUID) -> User:
        """Get a user by ID"""
        pass

    @abstractmethod
    async def update_user(self, user_id: UUID, data: Dict[str, Any]) -> User:
        """Update a user"""
        pass


class ClientInputPort(ABC):
    """Input port interface for client operations"""

    @abstractmethod
    async def create_client(self) -> Dict[str, str]:
        """Create a new client"""
        pass

    @abstractmethod
    async def authenticate_client(self, client_id: str, client_secret: str) -> str:
        """Authenticate a client and return token"""
        pass
