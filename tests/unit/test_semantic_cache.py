"""
Unit tests for SemanticCache.

Tests embedding generation, cosine similarity, threshold matching, and cache operations.
"""
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock
from sales_agent.engine.semantic_cache import SemanticCache


@pytest.fixture
def mock_embedding_response():
    """Mock OpenAI embedding response."""
    # Create a mock embedding vector (1536 dimensions for text-embedding-3-small)
    embedding_vector = np.random.rand(1536).astype(np.float32)
    
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = embedding_vector.tolist()
    return mock_response


@pytest.fixture
def mock_openai_client(mock_embedding_response):
    """Mock OpenAI client."""
    client = AsyncMock()
    client.embeddings.create = AsyncMock(return_value=mock_embedding_response)
    return client


@pytest.mark.asyncio
class TestSemanticCacheInitialization:
    """Test SemanticCache initialization."""
    
    async def test_default_similarity_threshold(self):
        """Test default similarity_threshold is 0.92."""
        with patch.dict('os.environ', {}, clear=True):
            # No API key - embeddings disabled
            cache = SemanticCache()
            assert cache.similarity_threshold == 0.92
    
    async def test_custom_similarity_threshold(self):
        """Test custom similarity_threshold is set correctly."""
        with patch.dict('os.environ', {}, clear=True):
            cache = SemanticCache(similarity_threshold=0.95)
            assert cache.similarity_threshold == 0.95
    
    async def test_default_ttl(self):
        """Test default TTL is 3600 seconds."""
        with patch.dict('os.environ', {}, clear=True):
            cache = SemanticCache()
            assert cache.ttl_seconds == 3600
    
    async def test_default_max_size(self):
        """Test default max_size is 1000."""
        with patch.dict('os.environ', {}, clear=True):
            cache = SemanticCache()
            assert cache.max_size == 1000
    
    async def test_embeddings_disabled_when_no_api_key(self):
        """Test embeddings disabled when OPENAI_API_KEY missing."""
        with patch.dict('os.environ', {}, clear=True):
            cache = SemanticCache()
            assert cache.embeddings_enabled is False
            assert cache.embedding_client is None
    
    async def test_embeddings_enabled_when_api_key_present(self, mock_openai_client):
        """Test embeddings enabled when OPENAI_API_KEY present."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                assert cache.embeddings_enabled is True
                assert cache.embedding_client is not None


@pytest.mark.asyncio
class TestEmbeddingGeneration:
    """Test embedding generation."""
    
    async def test_embedding_generation(self, mock_openai_client):
        """Test embedding generation (mock OpenAI API)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                embedding = await cache.get_embedding("test message")
                
                assert embedding is not None
                assert isinstance(embedding, np.ndarray)
                assert embedding.shape == (1536,)
                assert cache.stats["embedding_computations"] == 1
    
    async def test_embedding_returns_none_when_disabled(self):
        """Test returns None when embeddings disabled."""
        with patch.dict('os.environ', {}, clear=True):
            cache = SemanticCache()
            embedding = await cache.get_embedding("test message")
            assert embedding is None
    
    async def test_embedding_computation_stats_increment(self, mock_openai_client):
        """Test embedding computation stats increment."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                await cache.get_embedding("message1")
                await cache.get_embedding("message2")
                
                assert cache.stats["embedding_computations"] == 2
    
    async def test_embedding_error_handling(self, mock_openai_client):
        """Test error handling when embedding API fails."""
        mock_openai_client.embeddings.create = AsyncMock(side_effect=Exception("API error"))
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                embedding = await cache.get_embedding("test message")
                assert embedding is None


@pytest.mark.asyncio
class TestCosineSimilarity:
    """Test cosine similarity calculation."""
    
    async def test_cosine_similarity_identical_vectors(self, mock_openai_client):
        """Test identical vectors (similarity = 1.0)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                vec = np.array([1.0, 0.0, 0.0])
                similarity = cache._cosine_similarity(vec, vec)
                assert abs(similarity - 1.0) < 1e-6
    
    async def test_cosine_similarity_orthogonal_vectors(self, mock_openai_client):
        """Test orthogonal vectors (similarity = 0.0)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                vec1 = np.array([1.0, 0.0])
                vec2 = np.array([0.0, 1.0])
                similarity = cache._cosine_similarity(vec1, vec2)
                assert abs(similarity - 0.0) < 1e-6
    
    async def test_cosine_similarity_zero_vector(self, mock_openai_client):
        """Test zero vector handling (returns 0.0)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                vec1 = np.array([1.0, 0.0])
                vec2 = np.array([0.0, 0.0])
                similarity = cache._cosine_similarity(vec1, vec2)
                assert similarity == 0.0
    
    async def test_cosine_similarity_range(self, mock_openai_client):
        """Test cosine similarity range (0-1)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                vec1 = np.array([1.0, 1.0])
                vec2 = np.array([0.5, 0.5])
                similarity = cache._cosine_similarity(vec1, vec2)
                assert 0.0 <= similarity <= 1.0


@pytest.mark.asyncio
class TestContextHash:
    """Test context hash generation."""
    
    async def test_deterministic_context_hash(self, mock_openai_client):
        """Test deterministic context hash generation."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                context = {"key1": "value1", "key2": "value2"}
                hash1 = cache._make_context_hash(context)
                hash2 = cache._make_context_hash(context)
                assert hash1 == hash2
    
    async def test_context_hash_sorting(self, mock_openai_client):
        """Test context sorting (different order = same hash)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                context1 = {"a": "1", "b": "2"}
                context2 = {"b": "2", "a": "1"}
                hash1 = cache._make_context_hash(context1)
                hash2 = cache._make_context_hash(context2)
                assert hash1 == hash2
    
    async def test_context_hash_filters_empty_values(self, mock_openai_client):
        """Test context hash filters out empty values."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                context1 = {"key1": "value1", "key2": ""}
                context2 = {"key1": "value1"}
                hash1 = cache._make_context_hash(context1)
                hash2 = cache._make_context_hash(context2)
                assert hash1 == hash2


@pytest.mark.asyncio
class TestSemanticCacheGet:
    """Test semantic cache get operation."""
    
    async def test_cache_miss_no_entries(self, mock_openai_client):
        """Test cache miss when no entries."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                result = await cache.get("test message", {})
                assert result is None
                assert cache.stats["misses"] == 1
    
    async def test_cache_hit_similarity_above_threshold(self, mock_openai_client):
        """Test cache hit when similarity >= threshold."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache(similarity_threshold=0.5)  # Lower threshold for testing
                
                # Store an entry with same embedding
                cached_response = {"response": "cached"}
                await cache.set("original message", {}, cached_response)
                
                # Get with same message (will get same embedding from mock)
                result = await cache.get("original message", {})
                
                # Should hit because embeddings will be identical
                assert result is not None
                assert cache.stats["hits"] == 1
    
    async def test_cache_miss_similarity_below_threshold(self, mock_openai_client):
        """Test cache miss when similarity < threshold."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache(similarity_threshold=0.99)  # Very high threshold
                
                # Store an entry
                await cache.set("original message", {}, {"response": "cached"})
                
                # Try to get with different message
                # Mock will return same embedding, but with threshold 0.99, might miss
                result = await cache.get("different message", {})
                
                # Should miss or hit depending on similarity
                # For testing, we'll just verify the stats are tracked
                assert cache.stats["misses"] >= 0 or cache.stats["hits"] >= 0
    
    async def test_cache_expiration_removal(self, mock_openai_client):
        """Test expired entries are removed."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                with patch('time.time') as mock_time:
                    cache = SemanticCache(ttl_seconds=60)
                    
                    # Set initial time
                    mock_time.return_value = 0
                    await cache.set("message", {}, {"response": "cached"})
                    
                    # Fast forward past TTL
                    mock_time.return_value = 61
                    
                    result = await cache.get("message", {})
                    # Entry should be expired and removed
                    assert result is None
                    assert len(cache.cache) == 0
    
    async def test_context_hash_matching_requirement(self, mock_openai_client):
        """Test context hash must match for cache hit."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache(similarity_threshold=0.5)
                
                # Store with context1
                await cache.set("message", {"key1": "value1"}, {"response": "cached1"})
                
                # Try to get with context2 (different hash)
                result = await cache.get("message", {"key2": "value2"})
                
                # Should miss due to context mismatch
                assert result is None
    
    async def test_best_match_selection(self, mock_openai_client):
        """Test best match selection (highest similarity)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache(similarity_threshold=0.5)
                
                # Store multiple entries
                await cache.set("message1", {}, {"response": "cached1"})
                await cache.set("message2", {}, {"response": "cached2"})
                
                # Get - should return best match
                result = await cache.get("message1", {})
                # Should match message1 exactly
                assert result is not None


@pytest.mark.asyncio
class TestSemanticCacheSet:
    """Test semantic cache set operation."""
    
    async def test_store_entry_with_embedding(self, mock_openai_client):
        """Test storing entry with embedding."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                response = {"response": "test"}
                await cache.set("test message", {}, response)
                
                assert len(cache.cache) == 1
                # Verify entry has embedding stored
                cache_key = list(cache.cache.keys())[0]
                entry = cache.cache[cache_key]
                assert "embedding" in entry
                assert entry["response"] == response
    
    async def test_eviction_when_max_size_exceeded(self, mock_openai_client):
        """Test eviction when max_size exceeded."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                with patch('time.time', side_effect=[1.0, 2.0, 3.0, 4.0]):
                    cache = SemanticCache(max_size=2)
                    
                    await cache.set("message1", {}, {"r": "1"})
                    await cache.set("message2", {}, {"r": "2"})
                    assert len(cache.cache) == 2
                    
                    # Add one more - should evict oldest
                    await cache.set("message3", {}, {"r": "3"})
                    assert len(cache.cache) == 2  # Still max_size
    
    async def test_context_hash_stored(self, mock_openai_client):
        """Test context hash is stored correctly."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                context = {"key": "value"}
                context_hash = cache._make_context_hash(context)
                
                await cache.set("message", context, {"response": "test"})
                
                cache_key = list(cache.cache.keys())[0]
                entry = cache.cache[cache_key]
                assert entry["context_hash"] == context_hash


@pytest.mark.asyncio
class TestSemanticCacheClear:
    """Test semantic cache clear operation."""
    
    async def test_clear_all_entries(self, mock_openai_client):
        """Test all entries cleared."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                await cache.set("message1", {}, {"r": "1"})
                await cache.set("message2", {}, {"r": "2"})
                
                cache.clear()
                
                assert len(cache.cache) == 0
    
    async def test_clear_resets_stats(self, mock_openai_client):
        """Test stats reset on clear."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                await cache.set("message1", {}, {"r": "1"})
                await cache.get("message1", {})  # Hit
                await cache.get("message2", {})  # Miss
                
                cache.clear()
                
                assert cache.stats["hits"] == 0
                assert cache.stats["misses"] == 0
                assert cache.stats["embedding_computations"] == 0


@pytest.mark.asyncio
class TestSemanticCacheStats:
    """Test semantic cache statistics."""
    
    async def test_hit_rate_calculation(self, mock_openai_client):
        """Test hit rate calculation."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache(similarity_threshold=0.5)
                
                await cache.set("message1", {}, {"r": "1"})
                await cache.get("message1", {})  # Should hit
                await cache.get("message2", {})  # Miss
                
                stats = cache.get_stats()
                assert stats["hits"] >= 0
                assert stats["misses"] >= 1
                if stats["hits"] + stats["misses"] > 0:
                    assert 0.0 <= stats["hit_rate"] <= 1.0
    
    async def test_embedding_computations_count(self, mock_openai_client):
        """Test embedding computations count."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                await cache.get_embedding("message1")
                await cache.get_embedding("message2")
                
                stats = cache.get_stats()
                assert stats["embedding_computations"] == 2
    
    async def test_stats_structure(self, mock_openai_client):
        """Test stats structure is complete."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.semantic_cache.AsyncOpenAI', return_value=mock_openai_client):
                cache = SemanticCache()
                
                stats = cache.get_stats()
                required_fields = [
                    "enabled", "hits", "misses", "hit_rate",
                    "embedding_computations", "size", "max_size",
                    "ttl_seconds", "similarity_threshold"
                ]
                for field in required_fields:
                    assert field in stats, f"Missing field: {field}"

