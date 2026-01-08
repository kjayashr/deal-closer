"""
LLM Connection Pool for shared HTTP connections and client reuse.
Implements HTTP/2 connection pooling to reduce cold start latency.
"""
import os
import sys
import asyncio
import httpx
import logging
from anthropic import AsyncAnthropic
from typing import Optional

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config

logger = logging.getLogger(__name__)


class LLMConnectionPool:
    """Shared connection pool for LLM providers with HTTP/2 support."""
    
    def __init__(self, timeout: Optional[float] = None):
        """
        Initialize connection pool with shared HTTP client.
        
        Args:
            timeout: Request timeout in seconds (default: from config)
        """
        # Create shared HTTP client with HTTP/2 and connection pooling
        self.http_client = httpx.AsyncClient(
            http2=True,
            timeout=timeout or config.LLM_TIMEOUT_SECONDS,
            limits=httpx.Limits(
                max_keepalive_connections=config.HTTP_MAX_KEEPALIVE_CONNECTIONS,
                max_connections=config.HTTP_MAX_CONNECTIONS
            )
        )
        
        # Initialize Anthropic client with shared HTTP client
        api_key = config.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self.anthropic = AsyncAnthropic(
            api_key=api_key,
            http_client=self.http_client
        )
        
        self._warmed_up = False
    
    async def warmup(self):
        """
        Warm up connections by sending dummy requests.
        This establishes HTTP/2 connections before actual requests.
        """
        if self._warmed_up:
            return
        
        try:
            # Send a minimal warmup request to establish connections
            # Use a very simple prompt to minimize cost
            warmup_prompt = "Hi"
            
            # Start warmup but don't wait - fire and forget
            # This establishes the connection without blocking startup
            asyncio.create_task(self._warmup_request(warmup_prompt))
            
            self._warmed_up = True
            logger.info("LLM connection pool warmup initiated")
        except Exception as e:
            logger.warning(f"Connection warmup failed (non-critical): {str(e)}")
    
    async def _warmup_request(self, prompt: str):
        """Internal warmup request (fire and forget)."""
        try:
            await self.anthropic.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=1,
                messages=[{"role": "user", "content": prompt}]
            )
        except Exception as e:
            # Log but don't fail - warmup is best effort
            logger.debug(f"Warmup request completed with status: {str(e)}")
    
    async def close(self):
        """Close HTTP client and cleanup connections."""
        await self.http_client.aclose()
        logger.info("LLM connection pool closed")
    
    def get_anthropic_client(self) -> AsyncAnthropic:
        """Get the shared Anthropic client."""
        return self.anthropic

