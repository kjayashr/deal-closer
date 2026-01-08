"""
Utility functions for retry logic and error handling
"""
import os
import sys
import asyncio
import logging
from typing import Callable, Any, Optional, TypeVar
from functools import wraps

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[[], Any],
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts (default: from config)
        base_delay: Base delay in seconds (default: from config)
        max_delay: Maximum delay in seconds (default: from config)
        exceptions: Tuple of exceptions to catch and retry on
    
    Returns:
        Result of the function call
    
    Raises:
        Last exception if all attempts fail
    """
    # Use config defaults if not provided
    max_attempts = max_attempts or config.RETRY_MAX_ATTEMPTS
    base_delay = base_delay or config.RETRY_BASE_DELAY_SECONDS
    max_delay = max_delay or config.RETRY_MAX_DELAY_SECONDS
    
    last_exception = None
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            if attempt < max_attempts - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}. "
                    f"Retrying in {delay:.2f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_attempts} attempts failed. Last error: {str(e)}")
    
    raise last_exception

