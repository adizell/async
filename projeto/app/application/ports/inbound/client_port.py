# app/application/ports/inbound/client_port.py

from abc import ABC, abstractmethod
from typing import Dict


class IClientUseCase(ABC):
    """Interface for client-related use cases."""

    @abstractmethod
    def create_client(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def authenticate_client(self, client_id: str, client_secret: str) -> str:
        pass

    @abstractmethod
    def update_client_secret(self, client_id: str) -> Dict[str, str]:
        pass
