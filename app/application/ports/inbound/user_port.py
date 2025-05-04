# app/application/ports/inbound/user_port.py

from abc import ABC, abstractmethod
from uuid import UUID
from typing import Dict

from app.application.dtos.user_dto import UserCreate, UserOutput, UserUpdate, TokenData


class IUserUseCase(ABC):
    """Interface for user-related use cases."""

    @abstractmethod
    def register_user(self, user_data: UserCreate) -> UserOutput:
        pass

    @abstractmethod
    def authenticate_user(self, email: str, password: str) -> TokenData:
        pass

    @abstractmethod
    def update_user(self, user_id: UUID, data: UserUpdate) -> UserOutput:
        pass

    @abstractmethod
    def deactivate_user(self, user_id: UUID) -> Dict[str, str]:
        pass

    @abstractmethod
    def reactivate_user(self, user_id: UUID) -> Dict[str, str]:
        pass

    @abstractmethod
    def get_user_by_id(self, user_id: UUID) -> UserOutput:
        pass

    @abstractmethod
    def get_user_by_email(self, email: str) -> UserOutput:
        pass
