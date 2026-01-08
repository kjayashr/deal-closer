"""
Semantic Cache using embeddings for similarity-based caching.
Finds semantically similar messages and returns cached responses.
"""
import os
import sys
import json
import time
import logging
import hashlib
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from openai import AsyncOpenAI

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config

logger = logging.getLogger(__name__)


class SemanticCache:
    """In-memory semantic cache using embeddings for similarity matching."""
    
    def __init__(
        self,
        similarity_threshold: float = 0.92,
        ttl_seconds: int = 3600,
        max_size: int = 1000
    ):
        """
        Initialize semantic cache.
        
        Args:
            similarity_threshold: Minimum cosine similarity to consider a match (0.92 = very similar)
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
            max_size: Maximum number of entries before eviction (default: 1000)
        """
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        
        # Cache storage: {embedding_hash: {embedding, response, timestamp, context_hash}}
        self.cache: Dict[str, Dict[str, Any]] = {}
        
        # OpenAI client for embeddings
        api_key = config.OPENAI_API_KEY
        if api_key:
            self.embedding_client = AsyncOpenAI(api_key=api_key)
            self.embeddings_enabled = True
        else:
            self.embedding_client = None
            self.embeddings_enabled = False
            logger.warning("OPENAI_API_KEY not set, semantic cache disabled")
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "embedding_computations": 0
        }
    
    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Compute embedding for text using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array, or None if embeddings disabled
        """
        if not self.embeddings_enabled or not self.embedding_client:
            return None
        
        try:
            self.stats["embedding_computations"] += 1
            response = await self.embedding_client.embeddings.create(
                model=config.OPENAI_EMBEDDING_MODEL,
                input=text
            )
            embedding = np.array(response.data[0].embedding)
            return embedding
        except Exception as e:
            logger.error(f"Failed to compute embedding: {str(e)}")
            return None
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _make_context_hash(self, context: Dict) -> str:
        """
        Create hash of context for matching.
        
        Args:
            context: Context dictionary
            
        Returns:
            SHA256 hash string
        """
        # Create deterministic key from context (sorted)
        context_data = {k: v for k, v in sorted(context.items()) if v}
        context_json = json.dumps(context_data, sort_keys=True)
        return hashlib.sha256(context_json.encode()).hexdigest()
    
    async def get(
        self,
        message: str,
        context: Dict
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached response if semantically similar message exists.
        
        Args:
            message: Customer message
            context: Existing context dictionary
            
        Returns:
            Cached response dict if found and similar, None otherwise
        """
        if not self.embeddings_enabled:
            return None
        
        # Compute embedding for current message
        query_embedding = await self.get_embedding(message)
        if query_embedding is None:
            return None
        
        context_hash = self._make_context_hash(context)
        best_match = None
        best_similarity = 0.0
        
        # Find best matching entry
        current_time = time.time()
        for cache_key, entry in list(self.cache.items()):
            # Check if expired
            if current_time - entry["timestamp"] > self.ttl_seconds:
                del self.cache[cache_key]
                continue
            
            # Check context hash (must match for semantic similarity to be valid)
            if entry["context_hash"] != context_hash:
                continue
            
            # Compute similarity
            similarity = self._cosine_similarity(query_embedding, entry["embedding"])
            
            if similarity > best_similarity and similarity >= self.similarity_threshold:
                best_similarity = similarity
                best_match = entry
        
        if best_match:
            self.stats["hits"] += 1
            logger.debug(f"Semantic cache hit with similarity: {best_similarity:.3f}")
            return best_match["response"]
        
        self.stats["misses"] += 1
        return None
    
    async def set(
        self,
        message: str,
        context: Dict,
        response: Dict[str, Any]
    ):
        """
        Cache a response with its embedding.
        
        Args:
            message: Customer message
            context: Existing context dictionary
            response: Full response structure to cache
        """
        if not self.embeddings_enabled:
            return
        
        # Compute embedding for message
        embedding = await self.get_embedding(message)
        if embedding is None:
            return
        
        context_hash = self._make_context_hash(context)
        cache_key = hashlib.sha256(
            f"{message}:{context_hash}".encode()
        ).hexdigest()
        
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size and cache_key not in self.cache:
            # Remove oldest entry
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k]["timestamp"]
            )
            del self.cache[oldest_key]
        
        # Store entry
        self.cache[cache_key] = {
            "embedding": embedding,
            "response": response,
            "timestamp": time.time(),
            "context_hash": context_hash
        }
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0, "embedding_computations": 0}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hit rate, size, and counts
        """
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0.0
        
        return {
            "enabled": self.embeddings_enabled,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "embedding_computations": self.stats["embedding_computations"],
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl_seconds": self.ttl_seconds,
            "similarity_threshold": self.similarity_threshold
        }

