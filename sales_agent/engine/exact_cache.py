"""
Exact-match in-memory cache for API responses.
Uses message hash as key to provide fast cache lookups.
"""
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExactMatchCache:
    """In-memory exact-match cache with TTL support."""
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize cache with TTL and size limits.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 1 hour)
            max_size: Maximum number of entries before eviction (default: 1000)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, message: str, context: Dict) -> str:
        """
        Create cache key from message and context.
        
        Args:
            message: Customer message
            context: Existing context dictionary
            
        Returns:
            SHA256 hash string as cache key
        """
        # Create deterministic key from message + context
        key_data = {
            "message": message.lower().strip(),
            "context": {k: v for k, v in sorted(context.items()) if v}
        }
        key_json = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_json.encode()).hexdigest()
    
    def get(self, message: str, context: Dict) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired.
        
        Args:
            message: Customer message
            context: Existing context dictionary
            
        Returns:
            Cached response dict if found and valid, None otherwise
        """
        cache_key = self._make_key(message, context)
        
        if cache_key not in self.cache:
            self._misses += 1
            return None
        
        entry = self.cache[cache_key]
        
        # Check if expired
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            del self.cache[cache_key]
            self._misses += 1
            return None
        
        self._hits += 1
        return entry["response"]
    
    def set(self, message: str, context: Dict, response: Dict[str, Any]):
        """
        Cache a response.
        
        Args:
            message: Customer message
            context: Existing context dictionary
            response: Full response structure to cache
        """
        cache_key = self._make_key(message, context)
        
        # Evict oldest entry if cache is full (simple FIFO)
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            # Remove oldest entry
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k]["timestamp"]
            )
            del self.cache[oldest_key]
        
        self.cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self._hits = 0
        self._misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hit rate, size, and counts
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds
        }

