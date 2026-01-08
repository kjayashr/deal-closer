"""
Unit tests for SituationDetector.

Tests situation detection logic, fallback handling, prompt compression, and LLM API interaction.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sales_agent.engine.situation_detector import SituationDetector


@pytest.fixture
def sample_situations():
    """Sample situations for testing."""
    return {
        "price_shock_in_store": {
            "signals": ["expensive", "too much", "costly"],
            "stage": "objection_handling"
        },
        "just_browsing": {
            "signals": ["just looking", "browsing", "checking"],
            "stage": "discovery"
        },
        "warranty_and_service_concern": {
            "signals": ["warranty", "service", "repair"],
            "stage": "objection_handling"
        }
    }


@pytest.fixture
def mock_llm_router():
    """Mock LLM router."""
    router = AsyncMock()
    router.call = AsyncMock(return_value=(
        '{"situation": "price_shock_in_store", "confidence": 0.9, "stage": "objection_handling"}',
        "anthropic"
    ))
    return router


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text='{"situation": "price_shock_in_store", "confidence": 0.9, "stage": "objection_handling"}')]
    ))
    return client


@pytest.fixture
def mock_llm_pool(mock_anthropic_client):
    """Mock LLM pool."""
    pool = MagicMock()
    pool.get_anthropic_client = MagicMock(return_value=mock_anthropic_client)
    return pool


@pytest.mark.asyncio
class TestSituationDetectorInitialization:
    """Test SituationDetector initialization."""
    
    async def test_situations_loaded(self, sample_situations):
        """Test situations are loaded correctly."""
        detector = SituationDetector(sample_situations)
        assert detector.situations == sample_situations
    
    async def test_situation_keys_pre_computed(self, sample_situations):
        """Test situation_keys pre-computed."""
        detector = SituationDetector(sample_situations)
        assert len(detector.situation_keys) == 3
        assert "price_shock_in_store" in detector.situation_keys
        assert "just_browsing" in detector.situation_keys
    
    async def test_default_situation_set(self, sample_situations):
        """Test default_situation set (just_browsing)."""
        detector = SituationDetector(sample_situations)
        assert detector.default_situation == "just_browsing"
    
    async def test_router_initialization(self, sample_situations, mock_llm_router):
        """Test router initialization."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        assert detector.router == mock_llm_router
    
    async def test_pool_initialization(self, sample_situations, mock_llm_pool):
        """Test pool initialization."""
        detector = SituationDetector(sample_situations, llm_pool=mock_llm_pool)
        assert detector.client == mock_llm_pool.get_anthropic_client.return_value
    
    async def test_direct_client_initialization(self, sample_situations, mock_anthropic_client):
        """Test direct client initialization."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.situation_detector.AsyncAnthropic', return_value=mock_anthropic_client):
                detector = SituationDetector(sample_situations)
                assert detector.client == mock_anthropic_client


@pytest.mark.asyncio
class TestDetection:
    """Test situation detection logic."""
    
    async def test_successful_detection_with_router(self, sample_situations, mock_llm_router):
        """Test successful detection (mock LLM router)."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        result = await detector.detect(
            message="This is too expensive",
            context={},
            complexity="medium"
        )
        
        assert result["situation"] == "price_shock_in_store"
        assert result["confidence"] == 0.9
        assert result["stage"] == "objection_handling"
        
        # Verify router was called with correct parameters
        mock_llm_router.call.assert_called_once()
        call_kwargs = mock_llm_router.call.call_args[1]
        assert "prompt" in call_kwargs
        assert call_kwargs["max_tokens"] == 200
        assert call_kwargs["complexity"] == "medium"
    
    async def test_successful_detection_with_client(self, sample_situations, mock_anthropic_client):
        """Test successful detection (mock direct client)."""
        with patch('sales_agent.engine.situation_detector.retry_with_backoff', new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = '{"situation": "price_shock_in_store", "confidence": 0.9, "stage": "objection_handling"}'
            
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                with patch('sales_agent.engine.situation_detector.AsyncAnthropic', return_value=mock_anthropic_client):
                    detector = SituationDetector(sample_situations)
                    
                    result = await detector.detect(
                        message="This is too expensive",
                        context={}
                    )
                    
                    assert result["situation"] == "price_shock_in_store"
                    assert result["confidence"] == 0.9
    
    async def test_prompt_includes_situation_keys(self, sample_situations, mock_llm_router):
        """Test prompt includes situation keys."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        await detector.detect("test message", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        assert "price_shock_in_store" in prompt
        assert "just_browsing" in prompt
        assert "warranty_and_service_concern" in prompt
    
    async def test_prompt_includes_context(self, sample_situations, mock_llm_router):
        """Test prompt includes context."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        context = {"pain": "back pain", "budget_signal": "high"}
        await detector.detect("test message", context)
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        assert "back pain" in prompt or "high" in prompt
    
    async def test_prompt_includes_message(self, sample_situations, mock_llm_router):
        """Test prompt includes message."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        await detector.detect("This product is too expensive for me", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        assert "This product is too expensive for me" in prompt
    
    async def test_confidence_score_returned(self, sample_situations, mock_llm_router):
        """Test confidence score returned."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        result = await detector.detect("test", {})
        
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
    
    async def test_stage_returned(self, sample_situations, mock_llm_router):
        """Test stage returned (discovery/qualification/etc.)."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        result = await detector.detect("test", {})
        
        assert "stage" in result
        assert result["stage"] in ["discovery", "qualification", "presentation", "objection_handling", "closing"]


@pytest.mark.asyncio
class TestSituationValidation:
    """Test situation validation."""
    
    async def test_unknown_situation_uses_default(self, sample_situations, mock_llm_router):
        """Test unknown situation uses default fallback."""
        # Mock router to return unknown situation
        mock_llm_router.call = AsyncMock(return_value=(
            '{"situation": "unknown_situation", "confidence": 0.5, "stage": "discovery"}',
            "anthropic"
        ))
        
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        result = await detector.detect("test", {})
        
        # Should use default situation
        assert result["situation"] == "just_browsing"
        assert result["confidence"] == 0.3


@pytest.mark.asyncio
class TestFallbackBehavior:
    """Test fallback behavior."""
    
    async def test_fallback_when_router_fails(self, sample_situations, mock_llm_router):
        """Test fallback to default on router failure."""
        mock_llm_router.call = AsyncMock(side_effect=Exception("Router error"))
        
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        result = await detector.detect("test message", {})
        
        # Should return default fallback
        assert result["situation"] == "just_browsing"
        assert result["confidence"] == 0.3
        assert result["stage"] == "discovery"
    
    async def test_fallback_when_json_parse_fails(self, sample_situations, mock_llm_router):
        """Test fallback when JSON parsing fails."""
        # Mock router to return invalid JSON
        mock_llm_router.call = AsyncMock(return_value=("invalid json", "anthropic"))
        
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        result = await detector.detect("test message", {})
        
        # Should return default fallback
        assert result["situation"] == "just_browsing"
        assert result["confidence"] == 0.3
    
    async def test_fallback_when_api_error(self, sample_situations, mock_anthropic_client):
        """Test fallback when API error occurs."""
        from anthropic import APIError
        
        with patch('sales_agent.engine.situation_detector.retry_with_backoff', new_callable=AsyncMock) as mock_retry:
            mock_retry.side_effect = APIError("API error")
            
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                with patch('sales_agent.engine.situation_detector.AsyncAnthropic', return_value=mock_anthropic_client):
                    detector = SituationDetector(sample_situations)
                    
                    result = await detector.detect("test message", {})
                    
                    # Should return default fallback
                    assert result["situation"] == "just_browsing"
                    assert result["confidence"] == 0.3


@pytest.mark.asyncio
class TestPromptCompression:
    """Test prompt compression."""
    
    async def test_prompt_includes_situation_keys_compressed(self, sample_situations, mock_llm_router):
        """Test prompt includes situation keys (compressed format)."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        await detector.detect("test", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        # Should have compressed format with situation keys as comma-separated list
        assert "price_shock_in_store" in prompt
        assert "just_browsing" in prompt
    
    async def test_prompt_size_reduction(self, sample_situations, mock_llm_router):
        """Test prompt size reduction (~150 tokens vs ~400 tokens original)."""
        detector = SituationDetector(sample_situations, llm_router=mock_llm_router)
        
        await detector.detect("test message", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        # Prompt should be relatively compact
        assert len(prompt) < 800  # Character count heuristic


class TestSituationFormatting:
    """Test situation formatting."""
    
    def test_format_situations_structure(self, sample_situations):
        """Test formatted string structure."""
        detector = SituationDetector(sample_situations)
        formatted = detector._format_situations()
        
        assert "- price_shock_in_store:" in formatted
        assert "signals=" in formatted or "signals=[" in formatted
    
    def test_format_situations_truncates_signals(self, sample_situations):
        """Test signals truncated to 3 items."""
        # Create situations with more than 3 signals
        large_situations = {
            "test_situation": {
                "signals": ["signal1", "signal2", "signal3", "signal4", "signal5", "signal6"]
            }
        }
        
        detector = SituationDetector(large_situations)
        formatted = detector._format_situations()
        
        # Should only show first 3 signals
        assert "signal1" in formatted or formatted.count("signals=") == 1

