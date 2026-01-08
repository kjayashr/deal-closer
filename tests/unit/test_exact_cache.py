"""
Unit tests for ExactMatchCache.

Tests cache hit/miss, expiration, eviction, and stats functionality.
"""
import pytest
import time
from unittest.mock import patch
from sales_agent.engine.exact_cache import ExactMatchCache


@pytest.fixture
def cache():
    """Create a cache instance for testing."""
    return ExactMatchCache(ttl_seconds=60, max_size=100)


@pytest.fixture
def cache_short_ttl():
    """Create a cache instance with short TTL for expiration testing."""
    return ExactMatchCache(ttl_seconds=1, max_size=100)


class TestExactCacheInitialization:
    """Test cache initialization."""
    
    def test_default_ttl(self):
        """Test default TTL is 3600 seconds."""
        cache = ExactMatchCache()
        assert cache.ttl_seconds == 3600
    
    def test_custom_ttl(self):
        """Test custom TTL is set correctly."""
        cache = ExactMatchCache(ttl_seconds=120)
        assert cache.ttl_seconds == 120
    
    def test_default_max_size(self):
        """Test default max_size is 1000."""
        cache = ExactMatchCache()
        assert cache.max_size == 1000
    
    def test_custom_max_size(self):
        """Test custom max_size is set correctly."""
        cache = ExactMatchCache(max_size=500)
        assert cache.max_size == 500
    
    def test_initial_stats(self):
        """Test initial stats are zero."""
        cache = ExactMatchCache()
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["size"] == 0


class TestExactCacheKeyGeneration:
    """Test cache key generation."""
    
    def test_deterministic_key(self, cache):
        """Test same input always generates same key."""
        key1 = cache._make_key("test message", {"key": "value"})
        key2 = cache._make_key("test message", {"key": "value"})
        assert key1 == key2
    
    def test_case_insensitive(self, cache):
        """Test message is case-insensitive."""
        key1 = cache._make_key("Test Message", {})
        key2 = cache._make_key("test message", {})
        assert key1 == key2
    
    def test_context_sorting(self, cache):
        """Test context sorting (different order = same key)."""
        key1 = cache._make_key("test", {"a": "1", "b": "2"})
        key2 = cache._make_key("test", {"b": "2", "a": "1"})
        assert key1 == key2
    
    def test_empty_context(self, cache):
        """Test empty context handling."""
        key1 = cache._make_key("test", {})
        key2 = cache._make_key("test", {})
        assert key1 == key2
    
    def test_whitespace_normalization(self, cache):
        """Test whitespace normalization."""
        key1 = cache._make_key("  test message  ", {})
        key2 = cache._make_key("test message", {})
        assert key1 == key2
    
    def test_context_filters_empty_values(self, cache):
        """Test context filters out empty values."""
        key1 = cache._make_key("test", {"a": "1", "b": None, "c": ""})
        key2 = cache._make_key("test", {"a": "1"})
        assert key1 == key2


class TestExactCacheGet:
    """Test cache get operation."""
    
    def test_cache_miss(self, cache):
        """Test cache returns None on miss."""
        result = cache.get("test message", {})
        assert result is None
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0
    
    def test_cache_hit(self, cache):
        """Test cache returns cached value on hit."""
        response = {"response": "test"}
        cache.set("test message", {}, response)
        result = cache.get("test message", {})
        assert result == response
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0
    
    @patch('time.time')
    def test_cache_expiration(self, mock_time, cache_short_ttl):
        """Test cache expires entries after TTL."""
        # Set initial time
        mock_time.return_value = 0
        cache_short_ttl.set("test message", {}, {"response": "test"})
        
        # Fast forward time past TTL
        mock_time.return_value = 2
        
        result = cache_short_ttl.get("test message", {})
        assert result is None
        stats = cache_short_ttl.get_stats()
        assert stats["misses"] == 1
        assert stats["size"] == 0  # Expired entry removed
    
    def test_stats_increment_on_hit(self, cache):
        """Test stats increment on hit."""
        response = {"response": "test"}
        cache.set("test message", {}, response)
        
        # Multiple hits
        cache.get("test message", {})
        cache.get("test message", {})
        
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 0
    
    def test_stats_increment_on_miss(self, cache):
        """Test stats increment on miss."""
        cache.get("test message 1", {})
        cache.get("test message 2", {})
        
        stats = cache.get_stats()
        assert stats["misses"] == 2
        assert stats["hits"] == 0


class TestExactCacheSet:
    """Test cache set operation."""
    
    def test_store_new_entry(self, cache):
        """Test storing new entry."""
        response = {"response": "test"}
        cache.set("test message", {}, response)
        
        result = cache.get("test message", {})
        assert result == response
        assert cache.get_stats()["size"] == 1
    
    def test_update_existing_entry(self, cache):
        """Test updating existing entry."""
        cache.set("test message", {}, {"response": "old"})
        cache.set("test message", {}, {"response": "new"})
        
        result = cache.get("test message", {})
        assert result == {"response": "new"}
        assert cache.get_stats()["size"] == 1  # Still one entry
    
    def test_timestamp_set(self, cache):
        """Test timestamp is set correctly."""
        with patch('time.time', return_value=12345.0):
            cache.set("test message", {}, {"response": "test"})
            
            # Entry should have timestamp
            cache_key = cache._make_key("test message", {})
            assert cache_key in cache.cache
            assert cache.cache[cache_key]["timestamp"] == 12345.0


class TestExactCacheEviction:
    """Test cache eviction."""
    
    def test_eviction_when_max_size_exceeded(self):
        """Test eviction when max_size exceeded."""
        cache = ExactMatchCache(max_size=3)
        
        # Fill cache to max
        cache.set("message1", {}, {"r": "1"})
        cache.set("message2", {}, {"r": "2"})
        cache.set("message3", {}, {"r": "3"})
        assert cache.get_stats()["size"] == 3
        
        # Add one more - should evict oldest
        with patch('time.time', side_effect=[1.0, 2.0, 3.0, 4.0, 5.0]):
            cache.set("message1", {}, {"r": "1"})  # timestamp = 1.0
            cache.set("message2", {}, {"r": "2"})  # timestamp = 2.0
            cache.set("message3", {}, {"r": "3"})  # timestamp = 3.0
            
            # Add new entry - should evict message1 (oldest)
            cache.set("message4", {}, {"r": "4"})  # timestamp = 4.0
            
            # message1 should be evicted
            assert cache.get("message1", {}) is None
            assert cache.get("message2", {}) is not None
            assert cache.get("message3", {}) is not None
            assert cache.get("message4", {}) is not None
            assert cache.get_stats()["size"] == 3
    
    def test_no_eviction_when_entry_exists(self, cache):
        """Test no eviction when updating existing entry."""
        cache = ExactMatchCache(max_size=2)
        
        cache.set("message1", {}, {"r": "1"})
        cache.set("message2", {}, {"r": "2"})
        
        # Update existing entry - should not evict
        cache.set("message1", {}, {"r": "1-updated"})
        
        assert cache.get("message1", {}) == {"r": "1-updated"}
        assert cache.get("message2", {}) == {"r": "2"}
        assert cache.get_stats()["size"] == 2


class TestExactCacheClear:
    """Test cache clear operation."""
    
    def test_clear_all_entries(self, cache):
        """Test all entries cleared."""
        cache.set("message1", {}, {"r": "1"})
        cache.set("message2", {}, {"r": "2"})
        
        cache.clear()
        
        assert cache.get_stats()["size"] == 0
        assert cache.get("message1", {}) is None
        assert cache.get("message2", {}) is None
    
    def test_clear_resets_stats(self, cache):
        """Test stats reset on clear."""
        cache.set("message1", {}, {"r": "1"})
        cache.get("message1", {})  # Hit
        cache.get("message2", {})  # Miss
        
        cache.clear()
        
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestExactCacheStats:
    """Test cache statistics."""
    
    def test_hit_rate_calculation(self, cache):
        """Test hit rate calculation."""
        cache.set("message1", {}, {"r": "1"})
        
        cache.get("message1", {})  # Hit
        cache.get("message1", {})  # Hit
        cache.get("message2", {})  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == pytest.approx(2.0 / 3.0)
    
    def test_hit_rate_when_no_requests(self, cache):
        """Test hit rate when no requests (should be 0.0)."""
        stats = cache.get_stats()
        assert stats["hit_rate"] == 0.0
    
    def test_size_reporting(self, cache):
        """Test correct size reporting."""
        cache.set("message1", {}, {"r": "1"})
        cache.set("message2", {}, {"r": "2"})
        
        stats = cache.get_stats()
        assert stats["size"] == 2

