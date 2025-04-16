# app/domain/models/client_domain_model.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Client:
    """Domain model for Client entity"""
    id: int
    client_id: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
