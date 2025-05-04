# app/application/ports/inbound/__init__.py

from .user_port import IUserUseCase
from .client_port import IClientUseCase

__all__ = [
    "IUserUseCase",
    "IClientUseCase",
]
