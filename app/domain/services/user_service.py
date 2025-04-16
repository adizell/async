# app/domain/services/user_service.py

from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta

from app.domain.models.user_domain_model import User


class UserDomainService:
    """Domain service containing business logic for users"""

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """Validate password meets security requirements"""
        # Minimum 8 characters, at least one uppercase, one lowercase, one number, one special char
        if len(password) < 8:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)

        return has_upper and has_lower and has_digit and has_special

    @staticmethod
    def can_user_modify_another(actor_user: User, target_user: User) -> bool:
        """Check if a user can modify another user"""
        # Only superusers can modify other users
        # Users can always modify themselves
        return actor_user.is_superuser or actor_user.id == target_user.id
