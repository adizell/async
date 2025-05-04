# app/application/ports/outbound/user_repository_port.py

from abc import abstractmethod
from typing import Optional, Dict, Any

from app.application.ports.outbound.generic_repository import IRepository
from app.domain.models.user_domain_model import User


class IUserRepository(IRepository[User]):
    """User repository interface."""

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def create_with_password(self, user_data: Dict[str, Any]) -> User:
        pass

    @abstractmethod
    def update_with_password(self, user: User, user_data: Dict[str, Any]) -> User:
        pass
