# app/domain/services/client_service.py

from datetime import datetime, timedelta
from secrets import token_urlsafe


class ClientDomainService:
    """Domain service containing business logic for clients"""

    @staticmethod
    def generate_client_credentials() -> dict:
        """Generate secure client ID and secret"""
        return {
            "client_id": token_urlsafe(16),
            "client_secret": token_urlsafe(32)
        }

    @staticmethod
    def calculate_token_expiration(days: int = 365) -> datetime:
        """Calculate expiration date for client tokens"""
        return datetime.utcnow() + timedelta(days=days)
