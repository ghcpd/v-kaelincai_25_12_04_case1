"""
Idempotency via request ID deduplication cache.
"""

from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Cache entry with TTL."""
    request_id: str
    result: Any  # Cached result (serializable)
    created_at: datetime
    ttl_seconds: int
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        expiry = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.utcnow() > expiry


class IdempotencyCache:
    """In-memory LRU idempotency cache with TTL."""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries (LRU eviction)
            ttl_seconds: Time-to-live for each entry (default 1 hour)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list = []  # For LRU tracking
    
    def get(self, request_id: str) -> Optional[Any]:
        """Retrieve cached result."""
        if request_id not in self._cache:
            return None
        
        entry = self._cache[request_id]
        if entry.is_expired():
            # Evict expired entry
            del self._cache[request_id]
            self._access_order.remove(request_id)
            return None
        
        # Move to end (LRU)
        if request_id in self._access_order:
            self._access_order.remove(request_id)
        self._access_order.append(request_id)
        
        return entry.result
    
    def set(self, request_id: str, result: Any) -> None:
        """Store result in cache."""
        # Remove old entry if exists
        if request_id in self._cache:
            self._access_order.remove(request_id)
        
        # Evict LRU if at capacity
        if len(self._cache) >= self.max_size and request_id not in self._cache:
            lru_id = self._access_order.pop(0)
            del self._cache[lru_id]
        
        # Insert new entry
        self._cache[request_id] = CacheEntry(
            request_id=request_id,
            result=result,
            created_at=datetime.utcnow(),
            ttl_seconds=self.ttl_seconds,
        )
        self._access_order.append(request_id)
    
    def clear_expired(self) -> int:
        """Remove all expired entries; return count."""
        expired_keys = [
            k for k, v in self._cache.items()
            if v.is_expired()
        ]
        for k in expired_keys:
            del self._cache[k]
            self._access_order.remove(k)
        return len(expired_keys)
    
    def stats(self) -> Dict:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "utilization": len(self._cache) / self.max_size,
        }
    
    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()
        self._access_order.clear()
