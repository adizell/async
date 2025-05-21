# app/test/utils/test_sync_manager.py

# Para Rodar o Script:
# pytest app/test/utils/test_sync_manager.py -v

import pytest
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.shared.utils.sync_manager import SyncManager, ConflictResolutionStrategy, SyncConflict


@dataclass
class SampleRecord:
    """Sample record for testing sync manager."""
    id: int
    name: str
    value: float
    updated_at: datetime = None


class TestSyncManager:
    """Test suite for SyncManager class."""

    def test_detect_conflicts(self):
        """Test conflict detection between records."""
        # Create sample records
        server_record = SampleRecord(
            id=1,
            name="Server",
            value=10.5,
            updated_at=datetime.now()
        )

        client_record = SampleRecord(
            id=1,
            name="Client",
            value=20.5,
            updated_at=datetime.now() - timedelta(minutes=5)
        )

        # Create sync manager
        sync_manager = SyncManager[SampleRecord]()

        # Detect conflicts
        conflicts = sync_manager.detect_conflicts(server_record, client_record)

        # Should detect name and value conflicts
        assert "name" in conflicts
        assert "value" in conflicts
        assert "id" not in conflicts  # Same ID, no conflict
        assert "updated_at" not in conflicts  # Excluded from check

    def test_resolve_conflicts_server_wins(self):
        """Test conflict resolution with SERVER_WINS strategy."""
        # Create sample records
        server_record = SampleRecord(
            id=1,
            name="Server",
            value=10.5,
            updated_at=datetime.now()
        )

        client_record = SampleRecord(
            id=1,
            name="Client",
            value=20.5,
            updated_at=datetime.now() - timedelta(minutes=5)
        )

        # Create sync manager with SERVER_WINS strategy
        sync_manager = SyncManager[SampleRecord](
            conflict_strategy=ConflictResolutionStrategy.SERVER_WINS
        )

        # Detect conflicts
        conflicts = sync_manager.detect_conflicts(server_record, client_record)

        # Resolve conflicts
        resolved = sync_manager.resolve_conflicts(
            server_record,
            client_record,
            conflicts
        )

        # Server values should be kept
        assert resolved.name == "Server"
        assert resolved.value == 10.5

    def test_resolve_conflicts_client_wins(self):
        """Test conflict resolution with CLIENT_WINS strategy."""
        # Create sample records
        server_record = SampleRecord(
            id=1,
            name="Server",
            value=10.5,
            updated_at=datetime.now()
        )

        client_record = SampleRecord(
            id=1,
            name="Client",
            value=20.5,
            updated_at=datetime.now() - timedelta(minutes=5)
        )

        # Create sync manager with CLIENT_WINS strategy
        sync_manager = SyncManager[SampleRecord](
            conflict_strategy=ConflictResolutionStrategy.CLIENT_WINS
        )

        # Detect conflicts
        conflicts = sync_manager.detect_conflicts(server_record, client_record)

        # Resolve conflicts
        resolved = sync_manager.resolve_conflicts(
            server_record,
            client_record,
            conflicts
        )

        # Client values should be kept
        assert resolved.name == "Client"
        assert resolved.value == 20.5

    def test_resolve_conflicts_latest_wins(self):
        """Test conflict resolution with LATEST_WINS strategy."""
        # Create timestamps for testing
        server_time = datetime.now()
        client_time = datetime.now() - timedelta(minutes=5)

        # Server record is newer
        server_record = SampleRecord(
            id=1,
            name="Newer",
            value=10.5,
            updated_at=server_time
        )

        client_record = SampleRecord(
            id=1,
            name="Older",
            value=20.5,
            updated_at=client_time
        )

        # Create sync manager with LATEST_WINS strategy
        sync_manager = SyncManager[SampleRecord](
            conflict_strategy=ConflictResolutionStrategy.LATEST_WINS
        )

        # Detect conflicts
        conflicts = sync_manager.detect_conflicts(server_record, client_record)

        # Resolve conflicts
        resolved = sync_manager.resolve_conflicts(
            server_record,
            client_record,
            conflicts
        )

        # Server values should be kept (newer)
        assert resolved.name == "Newer"
        assert resolved.value == 10.5

        # Now test with client record newer
        client_record.updated_at = datetime.now()
        server_record.updated_at = datetime.now() - timedelta(minutes=5)

        # Detect and resolve conflicts again
        conflicts = sync_manager.detect_conflicts(server_record, client_record)
        resolved = sync_manager.resolve_conflicts(
            server_record,
            client_record,
            conflicts
        )

        # Client values should be kept (newer)
        assert resolved.name == "Older"
        assert resolved.value == 20.5

    def test_resolve_conflicts_mixed_strategies(self):
        """Test conflict resolution with different strategies per field."""
        server_record = SampleRecord(
            id=1,
            name="Server",
            value=10.5,
            updated_at=datetime.now()
        )

        client_record = SampleRecord(
            id=1,
            name="Client",
            value=20.5,
            updated_at=datetime.now() - timedelta(minutes=5)
        )

        # Create sync manager with default SERVER_WINS
        sync_manager = SyncManager[SampleRecord](
            conflict_strategy=ConflictResolutionStrategy.SERVER_WINS
        )

        # Detect conflicts
        conflicts = sync_manager.detect_conflicts(server_record, client_record)

        # Resolve with field-specific strategies
        resolved = sync_manager.resolve_conflicts(
            server_record,
            client_record,
            conflicts,
            field_strategies={
                "name": ConflictResolutionStrategy.SERVER_WINS,
                "value": ConflictResolutionStrategy.CLIENT_WINS
            }
        )

        # Server name, client value
        assert resolved.name == "Server"
        assert resolved.value == 20.5

    def test_sensitive_fields_merge(self):
        """Test that sensitive fields raise SyncConflict during merge."""
        server_record = SampleRecord(
            id=1,
            name="Server",
            value=10.5,
            updated_at=datetime.now()
        )

        client_record = SampleRecord(
            id=1,
            name="Client",
            value=20.5,
            updated_at=datetime.now() - timedelta(minutes=5)
        )

        # Create sync manager with MERGE strategy and sensitive field
        sync_manager = SyncManager[SampleRecord](
            conflict_strategy=ConflictResolutionStrategy.MERGE,
            sensitive_fields=["name"]
        )

        # Detect conflicts
        conflicts = sync_manager.detect_conflicts(server_record, client_record)

        # Attempt to resolve should raise SyncConflict for sensitive field
        with pytest.raises(SyncConflict) as exc_info:
            sync_manager.resolve_conflicts(
                server_record,
                client_record,
                conflicts
            )

        # Check that the exception contains correct field
        assert exc_info.value.field == "name"
