# app/application/ports/outbound/client_repository_port.py

from abc import abstractmethod
from typing import Optional, Dict

from app.application.ports.outbound.generic_repository import IRepository
from app.domain.models.client_domain_model import Client


class IClientRepository(IRepository[Client]):
    """Client repository interface."""

    @abstractmethod
    def get_by_client_id(self, client_id: str) -> Optional[Client]:
        pass

    @abstractmethod
    def create_with_credentials(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def update_secret(self, client_id: str) -> Dict[str, str]:
        pass
