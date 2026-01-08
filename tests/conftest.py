"""
Pytest configuration and shared fixtures for unit tests.

Provides common fixtures and mocks used across multiple test files.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


# =============================================================================
# LLM Client Mocks
# =============================================================================

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text='{"test": "response"}')]
    ))
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"test": "response"}'))]
    ))
    return client


@pytest.fixture
def mock_openai_embedding_client():
    """Mock OpenAI embedding client for testing."""
    import numpy as np
    
    client = MagicMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock(return_value=MagicMock(
        data=[MagicMock(embedding=np.random.rand(1536).astype(np.float32).tolist())]
    ))
    return client


# =============================================================================
# LLM Pool and Router Mocks
# =============================================================================

@pytest.fixture
def mock_llm_pool(mock_anthropic_client):
    """Mock LLM connection pool."""
    pool = MagicMock()
    pool.get_anthropic_client = MagicMock(return_value=mock_anthropic_client)
    pool.warmup = AsyncMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_llm_router():
    """Mock LLM router with racing support."""
    router = AsyncMock()
    router.call = AsyncMock(return_value=("test response", "anthropic"))
    router.get_stats = MagicMock(return_value={
        "anthropic": {"wins": 0, "errors": 0, "total": 0, "win_rate": 0.0, "error_rate": 0.0},
        "openai": {"wins": 0, "errors": 0, "total": 0, "win_rate": 0.0, "error_rate": 0.0}
    })
    router.reset_stats = MagicMock()
    return router


# =============================================================================
# Engine Mocks
# =============================================================================

@pytest.fixture
def mock_capture_engine():
    """Mock CaptureEngine for testing."""
    engine = AsyncMock()
    engine.extract = AsyncMock(return_value={
        "slots": {"pain": "back pain"},
        "new_quotes": ["too expensive"]
    })
    return engine


@pytest.fixture
def mock_situation_detector():
    """Mock SituationDetector for testing."""
    detector = AsyncMock()
    detector.detect = AsyncMock(return_value={
        "situation": "price_shock_in_store",
        "confidence": 0.9,
        "stage": "objection_handling"
    })
    return detector


@pytest.fixture
def mock_response_generator():
    """Mock ResponseGenerator for testing."""
    generator = AsyncMock()
    generator.generate = AsyncMock(return_value={
        "response": "I understand price is important to you.",
        "principle_used": "Loss Aversion"
    })
    return generator


# =============================================================================
# Cache Mocks
# =============================================================================

@pytest.fixture
def mock_exact_cache():
    """Mock ExactMatchCache for testing."""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    cache.clear = MagicMock()
    cache.get_stats = MagicMock(return_value={
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        "size": 0,
        "max_size": 1000,
        "ttl_seconds": 3600
    })
    return cache


@pytest.fixture
def mock_semantic_cache():
    """Mock SemanticCache for testing."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.clear = MagicMock()
    cache.get_stats = MagicMock(return_value={
        "enabled": True,
        "hits": 0,
        "misses": 0,
        "hit_rate": 0.0,
        "embedding_computations": 0,
        "size": 0,
        "max_size": 1000,
        "ttl_seconds": 3600,
        "similarity_threshold": 0.92
    })
    return cache


# =============================================================================
# Config Fixtures
# =============================================================================

@pytest.fixture
def sample_principles():
    """Sample principles for testing."""
    return [
        {
            "principle_id": "kahneman_loss_aversion_01",
            "name": "Loss Aversion",
            "definition": "People feel losses more strongly than gains",
            "mechanism": "Loss framing increases motivation",
            "intervention": "Frame in terms of what they'll lose",
            "source": {
                "author": "Kahneman",
                "book": "Thinking Fast and Slow",
                "chapter": 26,
                "page": 284
            }
        },
        {
            "principle_id": "voss_labeling_01",
            "name": "Labeling",
            "definition": "Label emotions to build rapport",
            "mechanism": "Acknowledgment builds trust",
            "intervention": "Name the emotion they're feeling",
            "source": {
                "author": "Voss",
                "book": "Never Split the Difference"
            }
        }
    ]


@pytest.fixture
def sample_situations():
    """Sample situations for testing."""
    return {
        "price_shock_in_store": {
            "signals": ["expensive", "too much"],
            "stage": "objection_handling"
        },
        "just_browsing": {
            "signals": ["just looking"],
            "stage": "discovery"
        }
    }


@pytest.fixture
def sample_capture_schema():
    """Sample capture schema for testing."""
    return {
        "capture_schema": {
            "slots": {
                "pain": {
                    "description": "Customer's pain point",
                    "priority": "high",
                    "listen_for": ["hurts", "pain"],
                    "feeds_principles": ["kahneman_loss_aversion_01"]
                },
                "budget_signal": {
                    "description": "Budget indication",
                    "priority": "medium",
                    "listen_for": ["expensive", "budget"],
                    "feeds_principles": ["cialdini_reciprocation_01"]
                }
            }
        }
    }


@pytest.fixture
def sample_selector_rules():
    """Sample selector rules for testing."""
    return {
        "principle_selector": {
            "version": "1.0",
            "domain": "retail",
            "rules": [
                {
                    "situation": "price_objection",
                    "when_context_has": ["pain"],
                    "use": "kahneman_loss_aversion_01"
                },
                {
                    "situation": "price_objection",
                    "when_context_missing": ["pain"],
                    "use": "voss_labeling_01"
                }
            ],
            "fallback": {
                "default": "voss_labeling_01",
                "when_no_context": "voss_labeling_01",
                "after_failed_attempt_1": "voss_labeling_01",
                "after_failed_attempt_2": "kahneman_loss_aversion_01"
            }
        }
    }


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_product_context():
    """Sample product context for testing."""
    return {
        "name": "ErgoChair",
        "price": 899,
        "category": "office furniture"
    }


@pytest.fixture
def sample_customer_message():
    """Sample customer message for testing."""
    return "This product is too expensive for my budget. My back has been hurting for 3 years."


@pytest.fixture
def sample_session_id():
    """Sample session ID for testing."""
    return "test-session-123"
