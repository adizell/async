# app/domain/models/user_domain_model.py

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import List, Optional


@dataclass
class User:
    """Domain model for User entity"""
    id: UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    groups: List[str] = None
    permissions: List[str] = None
