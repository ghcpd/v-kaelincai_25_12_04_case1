"""
Transactional outbox for audit trail and compensation.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import uuid
import json


class EventType(str, Enum):
    """Outbox event types."""
    ROUTE_COMPUTATION_STARTED = "ROUTE_COMPUTATION_STARTED"
    ROUTE_COMPUTATION_SUCCESS = "ROUTE_COMPUTATION_SUCCESS"
    ROUTE_COMPUTATION_FAILED = "ROUTE_COMPUTATION_FAILED"
    ROUTE_VALIDATION_ERROR = "ROUTE_VALIDATION_ERROR"
    ROUTE_TIMEOUT = "ROUTE_TIMEOUT"
    ROUTE_CACHED_HIT = "ROUTE_CACHED_HIT"


@dataclass
class OutboxEntry:
    """Entry in transactional outbox."""
    id: str
    request_id: str
    event_type: str  # EventType.value
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    is_processed: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "request_id": self.request_id,
            "event_type": self.event_type,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "is_processed": self.is_processed,
        }
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def create(
        cls,
        request_id: str,
        event_type: EventType,
        payload: Optional[Dict] = None,
    ) -> "OutboxEntry":
        """Create new outbox entry."""
        return cls(
            id=str(uuid.uuid4()),
            request_id=request_id,
            event_type=event_type.value,
            payload=payload or {},
        )


class OutboxStore:
    """In-memory outbox store (for testing; production would use database)."""
    
    def __init__(self):
        self._entries: Dict[str, OutboxEntry] = {}
        self._request_entries: Dict[str, List[str]] = {}  # request_id -> [entry_ids]
    
    def insert(self, entry: OutboxEntry) -> None:
        """Insert entry into outbox."""
        self._entries[entry.id] = entry
        if entry.request_id not in self._request_entries:
            self._request_entries[entry.request_id] = []
        self._request_entries[entry.request_id].append(entry.id)
    
    def update(self, entry: OutboxEntry) -> None:
        """Update entry."""
        if entry.id not in self._entries:
            raise ValueError(f"Entry {entry.id} not found")
        self._entries[entry.id] = entry
    
    def mark_processed(self, entry_id: str) -> None:
        """Mark entry as processed."""
        entry = self._entries.get(entry_id)
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")
        entry.is_processed = True
        entry.processed_at = datetime.utcnow()
    
    def get_by_request_id(self, request_id: str) -> List[OutboxEntry]:
        """Get all entries for a request."""
        entry_ids = self._request_entries.get(request_id, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]
    
    def get_unprocessed(self) -> List[OutboxEntry]:
        """Get all unprocessed entries."""
        return [e for e in self._entries.values() if not e.is_processed]
    
    def get_by_event_type(self, event_type: str) -> List[OutboxEntry]:
        """Get entries by event type."""
        return [e for e in self._entries.values() if e.event_type == event_type]
    
    def stats(self) -> dict:
        """Get outbox statistics."""
        total = len(self._entries)
        processed = sum(1 for e in self._entries.values() if e.is_processed)
        unprocessed = total - processed
        
        event_counts = {}
        for entry in self._entries.values():
            event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1
        
        return {
            "total_entries": total,
            "processed": processed,
            "unprocessed": unprocessed,
            "event_types": event_counts,
        }
    
    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
        self._request_entries.clear()
