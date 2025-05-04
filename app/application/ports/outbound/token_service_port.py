# app/application/ports/outbound/token_service_port.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime


class ITokenService(ABC):
    """Token handling interface."""

    @abstractmethod
    def create_access_token(self, subject: str, expires_delta: Optional[int] = None) -> str:
        pass

    @abstractmethod
    def create_refresh_token(self, subject: str, expires_delta: Optional[int] = None) -> str:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def revoke_token(self, token_id: str, expires_at: datetime) -> None:
        pass
