"""
Centralized configuration management with environment variable support.
All magic numbers should be configurable via environment variables.
"""
import os
from typing import Optional


class Config:
    """Application configuration with environment variable support."""
    
    # API Keys (Required)
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Cache Configuration
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))  # 1 hour default
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = float(os.getenv("SEMANTIC_CACHE_SIMILARITY_THRESHOLD", "0.92"))
    
    # Retry Configuration
    RETRY_MAX_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
    RETRY_BASE_DELAY_SECONDS: float = float(os.getenv("RETRY_BASE_DELAY_SECONDS", "1.0"))
    RETRY_MAX_DELAY_SECONDS: float = float(os.getenv("RETRY_MAX_DELAY_SECONDS", "10.0"))
    
    # LLM Configuration
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
    LLM_MAX_TOKENS_CAPTURE: int = int(os.getenv("LLM_MAX_TOKENS_CAPTURE", "500"))
    LLM_MAX_TOKENS_SITUATION: int = int(os.getenv("LLM_MAX_TOKENS_SITUATION", "200"))
    LLM_MAX_TOKENS_RESPONSE: int = int(os.getenv("LLM_MAX_TOKENS_RESPONSE", "150"))
    
    # Connection Pool Configuration
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "10"))
    HTTP_MAX_CONNECTIONS: int = int(os.getenv("HTTP_MAX_CONNECTIONS", "20"))
    
    # Model Names
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    ANTHROPIC_MODEL_FAST: str = os.getenv("ANTHROPIC_MODEL_FAST", "claude-sonnet-4-20250514")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_MODEL_FAST: str = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Orchestrator Configuration
    RECONCILE_CONFIDENCE_THRESHOLD: float = float(os.getenv("RECONCILE_CONFIDENCE_THRESHOLD", "0.7"))
    RECONCILE_NEW_SLOTS_THRESHOLD: int = int(os.getenv("RECONCILE_NEW_SLOTS_THRESHOLD", "3"))
    RECONCILE_NEW_QUOTES_THRESHOLD: int = int(os.getenv("RECONCILE_NEW_QUOTES_THRESHOLD", "1"))
    
    # Complexity Detection Thresholds
    COMPLEXITY_WORD_COUNT_SIMPLE: int = int(os.getenv("COMPLEXITY_WORD_COUNT_SIMPLE", "15"))
    COMPLEXITY_WORD_COUNT_COMPLEX: int = int(os.getenv("COMPLEXITY_WORD_COUNT_COMPLEX", "60"))
    COMPLEXITY_CONTEXT_RICHNESS_SIMPLE: int = int(os.getenv("COMPLEXITY_CONTEXT_RICHNESS_SIMPLE", "2"))
    COMPLEXITY_CONTEXT_RICHNESS_COMPLEX: int = int(os.getenv("COMPLEXITY_CONTEXT_RICHNESS_COMPLEX", "8"))
    
    # Response Generation Configuration
    RESPONSE_MAX_SENTENCES: int = int(os.getenv("RESPONSE_MAX_SENTENCES", "2"))
    RESPONSE_MAX_QUOTES: int = int(os.getenv("RESPONSE_MAX_QUOTES", "5"))
    RESPONSE_QUOTES_FOR_PROMPT: int = int(os.getenv("RESPONSE_QUOTES_FOR_PROMPT", "3"))
    
    # Default Fallback Values
    DEFAULT_SITUATION: str = os.getenv("DEFAULT_SITUATION", "just_browsing")
    DEFAULT_CONFIDENCE: float = float(os.getenv("DEFAULT_CONFIDENCE", "0.3"))
    DEFAULT_STAGE: str = os.getenv("DEFAULT_STAGE", "discovery")
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration values."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    
    @classmethod
    def is_openai_enabled(cls) -> bool:
        """Check if OpenAI is enabled."""
        return bool(cls.OPENAI_API_KEY)


# Global config instance
config = Config()

