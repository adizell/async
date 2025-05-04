# app/application/ports/outbound/generic_repository.py

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Any

T = TypeVar("T")


class IRepository(Generic[T], ABC):
    """Generic repository interface."""

    @abstractmethod
    def get(self, id: Any) -> Optional[T]:
        pass

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        pass

    @abstractmethod
    def create(self, entity: T) -> T:
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        pass

    @abstractmethod
    def delete(self, id: Any) -> None:
        pass
