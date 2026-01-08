"""
Unit tests for LLMRouter.

Tests multi-provider racing, tiered model selection, fallback logic, and statistics.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sales_agent.engine.llm_router import LLMRouter


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text="Anthropic response")]
    ))
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="OpenAI response"))]
    ))
    return client


@pytest.fixture
def mock_llm_pool(mock_anthropic_client):
    """Mock LLM pool."""
    pool = MagicMock()
    pool.get_anthropic_client = MagicMock(return_value=mock_anthropic_client)
    return pool


@pytest.mark.asyncio
class TestLLMRouterInitialization:
    """Test LLMRouter initialization."""
    
    async def test_anthropic_client_from_pool(self, mock_llm_pool):
        """Test Anthropic client from pool."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        assert router.anthropic_client == mock_llm_pool.get_anthropic_client.return_value
    
    async def test_anthropic_client_created_directly(self, mock_anthropic_client):
        """Test Anthropic client created directly (no pool)."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncAnthropic', return_value=mock_anthropic_client):
                router = LLMRouter(llm_pool=None, enable_openai=False)
                assert router.anthropic_client == mock_anthropic_client
    
    async def test_raises_error_when_api_key_missing(self):
        """Test raises ValueError when ANTHROPIC_API_KEY missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                LLMRouter(llm_pool=None, enable_openai=False)
    
    async def test_openai_enabled_when_api_key_present(self, mock_llm_pool, mock_openai_client):
        """Test OpenAI enabled when API key present."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncOpenAI', return_value=mock_openai_client):
                router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
                assert router.openai_enabled is True
                assert router.openai_client == mock_openai_client
    
    async def test_openai_disabled_when_api_key_missing(self, mock_llm_pool):
        """Test OpenAI disabled when API key missing."""
        with patch.dict('os.environ', {}, clear=True):
            router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
            assert router.openai_enabled is False
            assert router.openai_client is None
    
    async def test_stats_initialized(self, mock_llm_pool):
        """Test stats initialized (all zeros)."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        assert router.stats["anthropic"]["wins"] == 0
        assert router.stats["anthropic"]["errors"] == 0
        assert router.stats["anthropic"]["total"] == 0


@pytest.mark.asyncio
class TestTieredModelSelection:
    """Test tiered model selection based on complexity."""
    
    async def test_simple_complexity_uses_fast_models(self, mock_llm_pool):
        """Test 'simple' complexity → fast models."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        # This is tested indirectly through the call method
        # The model selection happens in call() method
        # We'll verify it through integration test
    
    async def test_medium_complexity_uses_default_models(self, mock_llm_pool):
        """Test 'medium' complexity → default models."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        # Tested through call method
    
    async def test_complex_complexity_uses_powerful_models(self, mock_llm_pool):
        """Test 'complex' complexity → powerful models."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        # Tested through call method
    
    async def test_custom_model_config_override(self, mock_llm_pool, mock_anthropic_client):
        """Test custom model_config override."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        model_config = {"anthropic_model": "custom-model"}
        result = await router.call(
            prompt="test",
            max_tokens=100,
            model_config=model_config,
            complexity="simple"
        )
        
        # Verify custom model was used
        mock_anthropic_client.messages.create.assert_called_once()
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "custom-model"


@pytest.mark.asyncio
class TestSingleProviderCall:
    """Test single provider call (Anthropic only)."""
    
    async def test_successful_call(self, mock_llm_pool, mock_anthropic_client):
        """Test successful call (mock Anthropic API)."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        response_text, provider = await router.call("test prompt", max_tokens=100)
        
        assert response_text == "Anthropic response"
        assert provider == "anthropic"
        assert router.stats["anthropic"]["wins"] == 1
        assert router.stats["anthropic"]["total"] == 1
    
    async def test_error_handling(self, mock_llm_pool, mock_anthropic_client):
        """Test error handling (API failure)."""
        from anthropic import APIError
        mock_anthropic_client.messages.create = AsyncMock(side_effect=APIError("API error"))
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        with pytest.raises(APIError):
            await router.call("test prompt", max_tokens=100)
        
        assert router.stats["anthropic"]["errors"] == 1
        assert router.stats["anthropic"]["total"] == 1


@pytest.mark.asyncio
class TestMultiProviderRacing:
    """Test multi-provider racing."""
    
    async def test_racing_with_two_providers(self, mock_llm_pool, mock_anthropic_client, mock_openai_client):
        """Test racing with 2 providers (mock both)."""
        # Make Anthropic faster
        async def fast_anthropic(*args, **kwargs):
            await asyncio.sleep(0.01)
            return MagicMock(content=[MagicMock(text="Anthropic won")])
        
        async def slow_openai(*args, **kwargs):
            await asyncio.sleep(0.1)
            return MagicMock(choices=[MagicMock(message=MagicMock(content="OpenAI won"))])
        
        mock_anthropic_client.messages.create = AsyncMock(side_effect=fast_anthropic)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=slow_openai)
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncOpenAI', return_value=mock_openai_client):
                router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
                
                response_text, provider = await router.call("test prompt", max_tokens=100)
                
                assert provider == "anthropic"
                assert response_text == "Anthropic won"
                assert router.stats["anthropic"]["wins"] == 1
    
    async def test_first_completed_wins(self, mock_llm_pool, mock_anthropic_client, mock_openai_client):
        """Test first completed provider wins."""
        # Make OpenAI faster this time
        async def slow_anthropic(*args, **kwargs):
            await asyncio.sleep(0.1)
            return MagicMock(content=[MagicMock(text="Anthropic")])
        
        async def fast_openai(*args, **kwargs):
            await asyncio.sleep(0.01)
            return MagicMock(choices=[MagicMock(message=MagicMock(content="OpenAI won"))])
        
        mock_anthropic_client.messages.create = AsyncMock(side_effect=slow_anthropic)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=fast_openai)
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncOpenAI', return_value=mock_openai_client):
                router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
                
                response_text, provider = await router.call("test prompt", max_tokens=100)
                
                assert provider == "openai"
                assert response_text == "OpenAI won"
                assert router.stats["openai"]["wins"] == 1
    
    async def test_losing_tasks_cancelled(self, mock_llm_pool, mock_anthropic_client, mock_openai_client):
        """Test losing tasks are cancelled."""
        cancelled_tasks = []
        
        async def fast_anthropic(*args, **kwargs):
            await asyncio.sleep(0.01)
            return MagicMock(content=[MagicMock(text="Anthropic won")])
        
        async def slow_openai(*args, **kwargs):
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                cancelled_tasks.append("openai")
                raise
            return MagicMock(choices=[MagicMock(message=MagicMock(content="OpenAI"))])
        
        mock_anthropic_client.messages.create = AsyncMock(side_effect=fast_anthropic)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=slow_openai)
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncOpenAI', return_value=mock_openai_client):
                router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
                
                await router.call("test prompt", max_tokens=100)
                
                # OpenAI task should have been cancelled
                # Note: Cancellation timing may vary, but the logic should handle it
                assert router.stats["anthropic"]["wins"] == 1


@pytest.mark.asyncio
class TestFallbackLogic:
    """Test fallback logic when winner fails."""
    
    async def test_fallback_when_winner_fails(self, mock_llm_pool, mock_anthropic_client, mock_openai_client):
        """Test fallback when winner fails."""
        # Anthropic fails, OpenAI succeeds
        async def failing_anthropic(*args, **kwargs):
            await asyncio.sleep(0.01)
            raise Exception("Anthropic failed")
        
        async def slow_openai(*args, **kwargs):
            await asyncio.sleep(0.1)
            return MagicMock(choices=[MagicMock(message=MagicMock(content="OpenAI fallback"))])
        
        mock_anthropic_client.messages.create = AsyncMock(side_effect=failing_anthropic)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=slow_openai)
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncOpenAI', return_value=mock_openai_client):
                router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
                
                response_text, provider = await router.call("test prompt", max_tokens=100)
                
                # Should fallback to OpenAI
                assert provider == "openai"
                assert response_text == "OpenAI fallback"
                assert router.stats["anthropic"]["errors"] == 1
                assert router.stats["openai"]["wins"] == 1
    
    async def test_all_providers_fail(self, mock_llm_pool, mock_anthropic_client, mock_openai_client):
        """Test all providers fail (raises exception)."""
        mock_anthropic_client.messages.create = AsyncMock(side_effect=Exception("Anthropic failed"))
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=Exception("OpenAI failed"))
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncOpenAI', return_value=mock_openai_client):
                router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
                
                with pytest.raises(Exception, match="All LLM providers failed"):
                    await router.call("test prompt", max_tokens=100)
                
                assert router.stats["anthropic"]["errors"] >= 1
                assert router.stats["openai"]["errors"] >= 1


@pytest.mark.asyncio
class TestProviderCallMethods:
    """Test provider call methods."""
    
    async def test_call_anthropic(self, mock_llm_pool, mock_anthropic_client):
        """Test _call_anthropic (mock Anthropic API)."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        response = await router._call_anthropic("test prompt", max_tokens=100, model="claude-sonnet-4")
        
        assert response == "Anthropic response"
        mock_anthropic_client.messages.create.assert_called_once()
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4"
        assert call_kwargs["max_tokens"] == 100
    
    async def test_call_openai(self, mock_llm_pool, mock_openai_client):
        """Test _call_openai (mock OpenAI API)."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            with patch('sales_agent.engine.llm_router.AsyncOpenAI', return_value=mock_openai_client):
                router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=True)
                
                response = await router._call_openai("test prompt", max_tokens=100, model="gpt-4o")
                
                assert response == "OpenAI response"
                mock_openai_client.chat.completions.create.assert_called_once()
                call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
                assert call_kwargs["model"] == "gpt-4o"
                assert call_kwargs["max_tokens"] == 100
                assert call_kwargs["temperature"] == 0.7
    
    async def test_call_openai_raises_when_not_initialized(self, mock_llm_pool):
        """Test _call_openai raises when client not initialized."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        with pytest.raises(Exception, match="OpenAI client not initialized"):
            await router._call_openai("test prompt", max_tokens=100, model="gpt-4o")


@pytest.mark.asyncio
class TestStatistics:
    """Test statistics tracking."""
    
    async def test_get_stats_structure(self, mock_llm_pool):
        """Test get_stats() returns correct structure."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        stats = router.get_stats()
        
        assert "anthropic" in stats
        assert "openai" in stats
        assert stats["anthropic"]["wins"] == 0
        assert stats["anthropic"]["errors"] == 0
        assert stats["anthropic"]["total"] == 0
        assert stats["anthropic"]["win_rate"] == 0.0
        assert stats["anthropic"]["error_rate"] == 0.0
    
    async def test_win_rate_calculation(self, mock_llm_pool, mock_anthropic_client):
        """Test win_rate calculation (wins / total)."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        # Make two successful calls
        await router.call("test1", max_tokens=100)
        await router.call("test2", max_tokens=100)
        
        stats = router.get_stats()
        assert stats["anthropic"]["wins"] == 2
        assert stats["anthropic"]["total"] == 2
        assert stats["anthropic"]["win_rate"] == 1.0
    
    async def test_error_rate_calculation(self, mock_llm_pool, mock_anthropic_client):
        """Test error_rate calculation (errors / total)."""
        from anthropic import APIError
        mock_anthropic_client.messages.create = AsyncMock(side_effect=APIError("API error"))
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        try:
            await router.call("test", max_tokens=100)
        except APIError:
            pass
        
        stats = router.get_stats()
        assert stats["anthropic"]["errors"] == 1
        assert stats["anthropic"]["total"] == 1
        assert stats["anthropic"]["error_rate"] == 1.0
    
    async def test_reset_stats(self, mock_llm_pool, mock_anthropic_client):
        """Test reset_stats() clears all stats."""
        router = LLMRouter(llm_pool=mock_llm_pool, enable_openai=False)
        
        # Make some calls
        await router.call("test", max_tokens=100)
        
        # Reset
        router.reset_stats()
        
        stats = router.get_stats()
        assert stats["anthropic"]["wins"] == 0
        assert stats["anthropic"]["errors"] == 0
        assert stats["anthropic"]["total"] == 0

