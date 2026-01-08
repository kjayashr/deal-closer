"""
Unit tests for ResponseGenerator.

Tests response generation, sentence validation, fallback responses, and principle formatting.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sales_agent.engine.response_generator import ResponseGenerator


@pytest.fixture
def sample_principles():
    """Sample principles for testing."""
    return [
        {
            "principle_id": "kahneman_loss_aversion_01",
            "name": "Loss Aversion",
            "definition": "People feel losses more strongly than gains",
            "mechanism": "Loss framing increases motivation",
            "intervention": "Frame in terms of what they'll lose"
        },
        {
            "principle_id": "voss_labeling_01",
            "name": "Labeling",
            "definition": "Label emotions to build rapport",
            "mechanism": "Acknowledgment builds trust",
            "intervention": "Name the emotion they're feeling"
        }
    ]


@pytest.fixture
def mock_llm_router():
    """Mock LLM router."""
    router = AsyncMock()
    router.call = AsyncMock(return_value=("This is a test response.", "anthropic"))
    return router


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text="This is a test response.")]
    ))
    return client


@pytest.fixture
def mock_llm_pool(mock_anthropic_client):
    """Mock LLM pool."""
    pool = MagicMock()
    pool.get_anthropic_client = MagicMock(return_value=mock_anthropic_client)
    return pool


@pytest.fixture
def response_generator_router(sample_principles, mock_llm_router):
    """Create ResponseGenerator with router."""
    return ResponseGenerator(sample_principles, llm_router=mock_llm_router)


@pytest.fixture
def response_generator_pool(sample_principles, mock_llm_pool):
    """Create ResponseGenerator with pool."""
    return ResponseGenerator(sample_principles, llm_pool=mock_llm_pool)


@pytest.fixture
def response_generator_direct(sample_principles):
    """Create ResponseGenerator with direct client."""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
        with patch('sales_agent.engine.response_generator.AsyncAnthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=MagicMock(
                content=[MagicMock(text="Test response.")]
            ))
            mock_anthropic.return_value = mock_client
            return ResponseGenerator(sample_principles)


class TestResponseGeneratorInitialization:
    """Test ResponseGenerator initialization."""
    
    def test_principles_dict_created(self, sample_principles):
        """Test principles dict is created correctly."""
        generator = ResponseGenerator(sample_principles)
        assert "kahneman_loss_aversion_01" in generator.principles
        assert generator.principles["kahneman_loss_aversion_01"]["name"] == "Loss Aversion"
    
    def test_router_initialization(self, sample_principles, mock_llm_router):
        """Test router initialization."""
        generator = ResponseGenerator(sample_principles, llm_router=mock_llm_router)
        assert generator.router == mock_llm_router
    
    def test_pool_initialization(self, sample_principles, mock_llm_pool):
        """Test pool initialization."""
        generator = ResponseGenerator(sample_principles, llm_pool=mock_llm_pool)
        assert generator.client == mock_llm_pool.get_anthropic_client.return_value
    
    def test_direct_client_initialization(self, sample_principles):
        """Test direct client initialization."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.response_generator.AsyncAnthropic') as mock_anthropic:
                mock_client = MagicMock()
                mock_anthropic.return_value = mock_client
                
                generator = ResponseGenerator(sample_principles)
                assert generator.client == mock_client
    
    def test_principle_cache_initialized(self, sample_principles):
        """Test principle cache initialized."""
        generator = ResponseGenerator(sample_principles)
        assert generator._principle_cache == {}


class TestPrincipleFormatting:
    """Test principle formatting."""
    
    def test_format_principle_section(self, response_generator_router):
        """Test formatted string structure."""
        principle = response_generator_router.principles["kahneman_loss_aversion_01"]
        formatted = response_generator_router._format_principle_section(principle)
        
        assert "Name: Loss Aversion" in formatted
        assert "Definition:" in formatted
        assert "Mechanism:" in formatted
        assert "Intervention:" in formatted
    
    def test_cache_usage(self, response_generator_router):
        """Test cache usage (second call uses cache)."""
        principle = response_generator_router.principles["kahneman_loss_aversion_01"]
        
        # First call
        formatted1 = response_generator_router._format_principle_section(principle)
        
        # Second call should use cache
        formatted2 = response_generator_router._format_principle_section(principle)
        
        assert formatted1 == formatted2
        assert "kahneman_loss_aversion_01" in response_generator_router._principle_cache
    
    def test_cache_key_principle_id(self, response_generator_router):
        """Test cache key is principle_id."""
        principle = response_generator_router.principles["kahneman_loss_aversion_01"]
        response_generator_router._format_principle_section(principle)
        
        assert "kahneman_loss_aversion_01" in response_generator_router._principle_cache


@pytest.mark.asyncio
class TestResponseGeneration:
    """Test response generation."""
    
    async def test_generation_with_router(self, response_generator_router, mock_llm_router):
        """Test successful generation (mock LLM router)."""
        principle = response_generator_router.principles["kahneman_loss_aversion_01"]
        
        result = await response_generator_router.generate(
            principle=principle,
            customer_quotes=["too expensive"],
            situation="price_shock_in_store",
            context={"pain": "back pain"},
            product_context={"name": "ErgoChair", "price": 899},
            complexity="medium"
        )
        
        assert result["response"] == "This is a test response."
        assert result["principle_used"] == "Loss Aversion"
        
        # Verify router was called with correct parameters
        mock_llm_router.call.assert_called_once()
        call_kwargs = mock_llm_router.call.call_args[1]
        assert "prompt" in call_kwargs
        assert call_kwargs["max_tokens"] == 150
        assert call_kwargs["complexity"] == "medium"
    
    async def test_generation_with_pool(self, response_generator_pool, mock_anthropic_client):
        """Test generation with pool (fallback to direct client)."""
        with patch('sales_agent.engine.response_generator.retry_with_backoff', new_callable=AsyncMock) as mock_retry:
            mock_retry.return_value = "Test response from pool."
            
            principle = response_generator_pool.principles["kahneman_loss_aversion_01"]
            
            result = await response_generator_pool.generate(
                principle=principle,
                customer_quotes=["too expensive"],
                situation="price_shock_in_store",
                context={}
            )
            
            assert result["response"] == "Test response from pool."
            assert result["principle_used"] == "Loss Aversion"
    
    async def test_prompt_includes_principle_info(self, response_generator_router, mock_llm_router):
        """Test prompt includes principle information."""
        principle = response_generator_router.principles["kahneman_loss_aversion_01"]
        
        await response_generator_router.generate(
            principle=principle,
            customer_quotes=["too expensive"],
            situation="price_shock_in_store",
            context={"pain": "back pain"},
            product_context={"name": "ErgoChair"}
        )
        
        call_kwargs = mock_llm_router.call.call_args[1]
        prompt = call_kwargs["prompt"]
        
        assert "Loss Aversion" in prompt
        assert "Frame in terms of what they'll lose" in prompt
        assert "too expensive" in prompt
        assert "price_shock_in_store" in prompt
        assert "back pain" in prompt
        assert "ErgoChair" in prompt
    
    async def test_fallback_when_router_fails(self, response_generator_router, mock_llm_router):
        """Test fallback when router fails."""
        mock_llm_router.call.side_effect = Exception("Router error")
        
        principle = response_generator_router.principles["kahneman_loss_aversion_01"]
        
        result = await response_generator_router.generate(
            principle=principle,
            customer_quotes=["too expensive"],
            situation="price_shock_in_store",
            context={}
        )
        
        # Should use fallback response
        assert result["response"] is not None
        assert "too expensive" in result["response"]
        assert result["principle_used"] == "Loss Aversion"


class TestSentenceValidation:
    """Test sentence validation (2-sentence limit)."""
    
    def test_one_sentence_kept(self, response_generator_router):
        """Test 1 sentence (kept as-is)."""
        text = "This is a single sentence."
        validated = response_generator_router._validate_sentence_count(text)
        assert validated == text
    
    def test_two_sentences_kept(self, response_generator_router):
        """Test 2 sentences (kept as-is)."""
        text = "This is the first sentence. This is the second sentence."
        validated = response_generator_router._validate_sentence_count(text)
        assert validated == text
    
    def test_three_sentences_truncated(self, response_generator_router):
        """Test 3+ sentences (truncated to first 2)."""
        text = "First sentence. Second sentence. Third sentence."
        validated = response_generator_router._validate_sentence_count(text)
        
        # Should be truncated to first 2 sentences
        assert "First sentence" in validated
        assert "Second sentence" in validated
        assert "Third sentence" not in validated
    
    def test_sentence_pattern_matching(self, response_generator_router):
        """Test sentence pattern matching (. ! ?)."""
        text = "First sentence! Second sentence? Third sentence."
        validated = response_generator_router._validate_sentence_count(text)
        
        # Should recognize all three sentence endings
        assert "First sentence" in validated
        assert "Second sentence" in validated
    
    def test_no_sentences_found_returns_original(self, response_generator_router):
        """Test edge case: no sentences found (returns original text)."""
        text = "No sentence endings here"
        validated = response_generator_router._validate_sentence_count(text)
        assert validated == text
    
    def test_whitespace_handling(self, response_generator_router):
        """Test whitespace handling."""
        text = "  First sentence.  Second sentence.  "
        validated = response_generator_router._validate_sentence_count(text)
        
        # Should handle whitespace correctly
        assert "First sentence" in validated
        assert "Second sentence" in validated


class TestFallbackResponse:
    """Test fallback response generation."""
    
    def test_fallback_with_quotes(self, response_generator_router):
        """Test fallback uses last quote when available."""
        fallback = response_generator_router._generate_fallback_response(
            customer_quotes=["first quote", "last quote"],
            situation="price_shock_in_store"
        )
        
        assert "last quote" in fallback
        assert "first quote" not in fallback
    
    def test_fallback_without_quotes(self, response_generator_router):
        """Test fallback uses default response when no quotes."""
        fallback = response_generator_router._generate_fallback_response(
            customer_quotes=[],
            situation="just_browsing"
        )
        
        assert "help you find" in fallback.lower() or "brings you" in fallback.lower()


class TestQuoteFormatting:
    """Test quote formatting."""
    
    def test_format_quotes_with_quotes(self, response_generator_router):
        """Test formatted quotes with proper structure."""
        formatted = response_generator_router._format_quotes([
            "quote 1",
            "quote 2"
        ])
        
        assert 'quote 1' in formatted
        assert 'quote 2' in formatted
        assert formatted.count('-') == 2
    
    def test_format_quotes_empty_list(self, response_generator_router):
        """Test empty quotes list."""
        formatted = response_generator_router._format_quotes([])
        assert "No quotes captured yet" in formatted

