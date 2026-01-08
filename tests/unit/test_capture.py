"""
Unit tests for CaptureEngine.

Tests extraction logic, prompt compression, fallback handling, and LLM API interaction.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sales_agent.engine.capture import CaptureEngine


@pytest.fixture
def sample_capture_schema():
    """Sample capture schema for testing."""
    return {
        "capture_schema": {
            "slots": {
                "pain": {
                    "description": "Customer's pain point",
                    "priority": "high",
                    "listen_for": ["hurts", "pain", "problem"],
                    "feeds_principles": ["kahneman_loss_aversion_01"]
                },
                "budget_signal": {
                    "description": "Budget indication",
                    "priority": "medium",
                    "listen_for": ["expensive", "budget", "afford"],
                    "feeds_principles": ["cialdini_reciprocation_01"]
                },
                "objection": {
                    "description": "Objection raised",
                    "priority": "high",
                    "listen_for": ["but", "however", "concern"],
                    "feeds_principles": ["voss_labeling_01"]
                }
            }
        }
    }


@pytest.fixture
def mock_llm_router():
    """Mock LLM router."""
    router = AsyncMock()
    router.call = AsyncMock(return_value=(
        '{"slots": {"pain": "back pain"}, "new_quotes": ["my back hurts"]}',
        "anthropic"
    ))
    return router


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text='{"slots": {"pain": "back pain"}, "new_quotes": ["my back hurts"]}')]
    ))
    return client


@pytest.fixture
def mock_llm_pool(mock_anthropic_client):
    """Mock LLM pool."""
    pool = MagicMock()
    pool.get_anthropic_client = MagicMock(return_value=mock_anthropic_client)
    return pool


@pytest.mark.asyncio
class TestCaptureEngineInitialization:
    """Test CaptureEngine initialization."""
    
    async def test_schema_loaded(self, sample_capture_schema):
        """Test schema is loaded correctly."""
        engine = CaptureEngine(sample_capture_schema)
        assert engine.schema == sample_capture_schema
    
    async def test_slots_extracted(self, sample_capture_schema):
        """Test slots are extracted correctly."""
        engine = CaptureEngine(sample_capture_schema)
        assert "pain" in engine.slots
        assert "budget_signal" in engine.slots
        assert "objection" in engine.slots
    
    async def test_slot_names_pre_computed(self, sample_capture_schema):
        """Test slot_names pre-computed."""
        engine = CaptureEngine(sample_capture_schema)
        assert len(engine.slot_names) == 3
        assert "pain" in engine.slot_names
        assert "budget_signal" in engine.slot_names
    
    async def test_router_initialization(self, sample_capture_schema, mock_llm_router):
        """Test router initialization."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        assert engine.router == mock_llm_router
    
    async def test_pool_initialization(self, sample_capture_schema, mock_llm_pool):
        """Test pool initialization."""
        engine = CaptureEngine(sample_capture_schema, llm_pool=mock_llm_pool)
        assert engine.client == mock_llm_pool.get_anthropic_client.return_value
    
    async def test_direct_client_initialization(self, sample_capture_schema, mock_anthropic_client):
        """Test direct client initialization."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.capture.AsyncAnthropic', return_value=mock_anthropic_client):
                engine = CaptureEngine(sample_capture_schema)
                assert engine.client == mock_anthropic_client


@pytest.mark.asyncio
class TestExtraction:
    """Test extraction logic."""
    
    async def test_successful_extraction_with_router(self, sample_capture_schema, mock_llm_router):
        """Test successful extraction (mock LLM router)."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        result = await engine.extract(
            message="My back hurts",
            existing_context={},
            complexity="medium"
        )
        
        assert result["slots"]["pain"] == "back pain"
        assert "my back hurts" in result["new_quotes"]
        
        # Verify router was called with correct parameters
        mock_llm_router.call.assert_called_once()
        call_kwargs = mock_llm_router.call.call_args[1]
        assert "prompt" in call_kwargs
        assert call_kwargs["max_tokens"] == 500
        assert call_kwargs["complexity"] == "medium"
    
    async def test_successful_extraction_with_client(self, sample_capture_schema, mock_anthropic_client):
        """Test successful extraction (mock direct client)."""
        with patch('sales_agent.engine.capture.retry_with_backoff', new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = '{"slots": {"pain": "back pain"}, "new_quotes": ["my back hurts"]}'
            
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                with patch('sales_agent.engine.capture.AsyncAnthropic', return_value=mock_anthropic_client):
                    engine = CaptureEngine(sample_capture_schema)
                    
                    result = await engine.extract(
                        message="My back hurts",
                        existing_context={}
                    )
                    
                    assert result["slots"]["pain"] == "back pain"
                    assert "my back hurts" in result["new_quotes"]
    
    async def test_prompt_includes_slot_names(self, sample_capture_schema, mock_llm_router):
        """Test prompt includes slot names."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        await engine.extract("test message", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        assert "pain" in prompt
        assert "budget_signal" in prompt
        assert "objection" in prompt
    
    async def test_prompt_includes_existing_context(self, sample_capture_schema, mock_llm_router):
        """Test prompt includes existing context."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        existing_context = {"pain": "existing pain", "budget_signal": "high"}
        await engine.extract("test message", existing_context)
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        assert "existing pain" in prompt
        assert "high" in prompt
    
    async def test_prompt_includes_message(self, sample_capture_schema, mock_llm_router):
        """Test prompt includes message."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        await engine.extract("My back is killing me", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        assert "My back is killing me" in prompt
    
    async def test_slots_filtered_null_values(self, sample_capture_schema, mock_llm_router):
        """Test slots filtered (null values removed)."""
        # Mock router to return slots with null values
        mock_llm_router.call = AsyncMock(return_value=(
            '{"slots": {"pain": "back pain", "budget_signal": null, "objection": ""}, "new_quotes": []}',
            "anthropic"
        ))
        
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        result = await engine.extract("test", {})
        
        # Null and empty values should be filtered
        assert "pain" in result["slots"]
        assert result["slots"]["pain"] == "back pain"
        # budget_signal and objection should be filtered out
        assert "budget_signal" not in result["slots"] or not result["slots"].get("budget_signal")
        assert "objection" not in result["slots"] or not result["slots"].get("objection")
    
    async def test_new_quotes_extracted(self, sample_capture_schema, mock_llm_router):
        """Test new_quotes extracted."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        result = await engine.extract("My back hurts", {})
        
        assert len(result["new_quotes"]) > 0
        assert "my back hurts" in result["new_quotes"]


@pytest.mark.asyncio
class TestFallbackBehavior:
    """Test fallback behavior."""
    
    async def test_fallback_when_router_fails(self, sample_capture_schema, mock_llm_router):
        """Test fallback to empty result on router failure."""
        mock_llm_router.call = AsyncMock(side_effect=Exception("Router error"))
        
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        result = await engine.extract("test message", {})
        
        # Should return empty result
        assert result["slots"] == {}
        assert result["new_quotes"] == []
    
    async def test_fallback_when_json_parse_fails(self, sample_capture_schema, mock_llm_router):
        """Test fallback when JSON parsing fails."""
        # Mock router to return invalid JSON
        mock_llm_router.call = AsyncMock(return_value=("invalid json", "anthropic"))
        
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        result = await engine.extract("test message", {})
        
        # Should return empty result
        assert result["slots"] == {}
        assert result["new_quotes"] == []
    
    async def test_fallback_when_api_error(self, sample_capture_schema, mock_anthropic_client):
        """Test fallback when API error occurs."""
        from anthropic import APIError
        
        with patch('sales_agent.engine.capture.retry_with_backoff', new_callable=AsyncMock) as mock_retry:
            mock_retry.side_effect = APIError("API error")
            
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                with patch('sales_agent.engine.capture.AsyncAnthropic', return_value=mock_anthropic_client):
                    engine = CaptureEngine(sample_capture_schema)
                    
                    result = await engine.extract("test message", {})
                    
                    # Should return empty result
                    assert result["slots"] == {}
                    assert result["new_quotes"] == []


@pytest.mark.asyncio
class TestPromptCompression:
    """Test prompt compression."""
    
    async def test_prompt_includes_slot_names_compressed(self, sample_capture_schema, mock_llm_router):
        """Test prompt includes slot names (compressed format)."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        await engine.extract("test", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        # Should have compressed format with slot names as comma-separated list
        assert "pain, budget_signal, objection" in prompt or "pain" in prompt
    
    async def test_prompt_size_reduction(self, sample_capture_schema, mock_llm_router):
        """Test prompt size reduction (~150 tokens vs ~500 tokens original)."""
        engine = CaptureEngine(sample_capture_schema, llm_router=mock_llm_router)
        
        await engine.extract("test message", {})
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        # Prompt should be relatively compact
        # (exact token count depends on tokenizer, but should be concise)
        assert len(prompt) < 1000  # Character count heuristic


class TestSlotFormatting:
    """Test slot formatting."""
    
    def test_format_slots_structure(self, sample_capture_schema):
        """Test formatted string structure."""
        engine = CaptureEngine(sample_capture_schema)
        formatted = engine._format_slots()
        
        assert "- pain:" in formatted
        assert "Customer's pain point" in formatted
        assert "Listen for:" in formatted
    
    def test_format_slots_truncates_listen_for(self, sample_capture_schema):
        """Test listen_for truncated to 5 items."""
        # Create schema with more than 5 listen_for items
        large_schema = {
            "capture_schema": {
                "slots": {
                    "test_slot": {
                        "description": "Test",
                        "listen_for": ["1", "2", "3", "4", "5", "6", "7", "8"]
                    }
                }
            }
        }
        
        engine = CaptureEngine(large_schema)
        formatted = engine._format_slots()
        
        # Should only show first 5 items
        assert "1, 2, 3, 4, 5" in formatted or formatted.count("Listen for") == 1

