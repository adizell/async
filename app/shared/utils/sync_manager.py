# app/shared/utils/sync_manager.py

"""
Utilities for handling offline-to-online synchronization.

This module provides tools for detecting and resolving conflicts
when synchronizing data between offline clients and the API.
"""

from datetime import datetime
from typing import Dict, List, Any, TypeVar, Generic, Optional
from enum import Enum

from app.shared.utils.datetime_utils import DateTimeUtil

T = TypeVar('T')


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving synchronization conflicts."""
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"
    LATEST_WINS = "latest_wins"
    MERGE = "merge"


class SyncConflict(Exception):
    """Exception raised when a synchronization conflict is detected."""

    def __init__(self, server_record: Any, client_record: Any, field: str):
        self.server_record = server_record
        self.client_record = client_record
        self.field = field
        super().__init__(f"Conflict detected in field '{field}'")


class SyncManager(Generic[T]):
    """
    Manager for synchronizing data between offline clients and the API.

    Handles conflict detection and resolution based on timestamps.
    """

    def __init__(
            self,
            timestamp_field: str = "updated_at",
            conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LATEST_WINS,
            sensitive_fields: List[str] = None
    ):
        """
        Initialize the sync manager.

        Args:
            timestamp_field: Field name used for timestamp comparison
            conflict_strategy: Strategy to resolve conflicts
            sensitive_fields: Fields that need special conflict resolution
        """
        self.timestamp_field = timestamp_field
        self.conflict_strategy = conflict_strategy
        self.sensitive_fields = sensitive_fields or []

    def detect_conflicts(
            self,
            server_record: T,
            client_record: T,
            key_fields: List[str] = None
    ) -> List[str]:
        """
        Detect conflicts between server and client records.

        Args:
            server_record: Record from server
            client_record: Record from client
            key_fields: Fields to check for conflicts (None = all fields)

        Returns:
            List of field names with conflicts
        """
        conflicts = []

        # Determinar campos a verificar
        if key_fields is None:
            # Usar todos os campos exceto o timestamp
            key_fields = [
                field for field in dir(server_record)
                if not field.startswith('_') and field != self.timestamp_field
                   and not callable(getattr(server_record, field))
            ]

        # Verificar conflitos em cada campo
        for field in key_fields:
            server_value = getattr(server_record, field, None)
            client_value = getattr(client_record, field, None)

            if server_value != client_value:
                conflicts.append(field)

        return conflicts

    def resolve_conflicts(
            self,
            server_record: T,
            client_record: T,
            conflict_fields: List[str],
            field_strategies: Dict[str, ConflictResolutionStrategy] = None
    ) -> T:
        """
        Resolve conflicts between server and client records.

        Args:
            server_record: Record from server
            client_record: Record from client
            conflict_fields: Fields with conflicts
            field_strategies: Specific resolution strategies for fields

        Returns:
            Resolved record
        """
        result = server_record  # Começar com o registro do servidor
        field_strategies = field_strategies or {}

        # Resolver cada conflito
        for field in conflict_fields:
            strategy = field_strategies.get(field, self.conflict_strategy)

            if strategy == ConflictResolutionStrategy.SERVER_WINS:
                # Manter o valor do servidor (já está em result)
                pass

            elif strategy == ConflictResolutionStrategy.CLIENT_WINS:
                # Usar o valor do cliente
                setattr(result, field, getattr(client_record, field))

            elif strategy == ConflictResolutionStrategy.LATEST_WINS:
                # Comparar timestamps e usar o mais recente
                server_time = getattr(server_record, self.timestamp_field, None)
                client_time = getattr(client_record, self.timestamp_field, None)

                if not server_time or not client_time:
                    # Se um dos timestamps está faltando, manter o servidor
                    continue

                # Garantir que ambos estão em UTC para comparação justa
                if server_time.tzinfo is None:
                    server_time = server_time.replace(tzinfo=DateTimeUtil.UTC)

                if client_time.tzinfo is None:
                    client_time = client_time.replace(tzinfo=DateTimeUtil.UTC)

                if client_time > server_time:
                    setattr(result, field, getattr(client_record, field))

            elif strategy == ConflictResolutionStrategy.MERGE:
                # Lógica específica para campos que podem ser mesclados
                # Implementação depende do tipo do campo
                if field in self.sensitive_fields:
                    # Para campos sensíveis, não realizar mesclagem automática
                    raise SyncConflict(server_record, client_record, field)

        # Atualizar o timestamp para o momento atual
        setattr(result, self.timestamp_field, DateTimeUtil.for_storage())

        return result


# Classe específica para endpoint de sincronização
class SyncEndpoint:
    """
    Utility class for handling synchronization in API endpoints.
    """

    @staticmethod
    def prepare_sync_response(
            updated_since: Optional[datetime],
            items: List[Dict[str, Any]],
            server_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Prepare a standardized response for sync endpoints.

        Args:
            updated_since: Timestamp from client's last sync
            items: List of items to synchronize
            server_timestamp: Current server timestamp (None = use current time)

        Returns:
            Dictionary with sync metadata and items
        """
        if server_timestamp is None:
            server_timestamp = DateTimeUtil.utcnow()

        return {
            "sync_timestamp": DateTimeUtil.format_iso(server_timestamp),
            "items_count": len(items),
            "items": items,
            "client_timestamp": DateTimeUtil.format_iso(updated_since) if updated_since else None
        }
