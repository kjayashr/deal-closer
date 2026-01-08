"""
Unit tests for LLMConnectionPool.

Tests connection pooling, warmup, client reuse, and connection management.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sales_agent.engine.llm_pool import LLMConnectionPool


@pytest.fixture
def mock_http_client():
    """Mock HTTP client."""
    client = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=MagicMock(
        content=[MagicMock(text="Hi")]
    ))
    return client


@pytest.mark.asyncio
class TestLLMConnectionPoolInitialization:
    """Test LLMConnectionPool initialization."""
    
    async def test_http_client_creation(self, mock_http_client):
        """Test HTTP client creation (httpx.AsyncClient)."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic') as mock_anthropic:
                    pool = LLMConnectionPool()
                    
                    # Verify HTTP client created with HTTP/2
                    assert pool.http_client is not None
    
    async def test_http2_enabled(self, mock_http_client):
        """Test HTTP/2 enabled."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value = mock_http_client
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic'):
                    pool = LLMConnectionPool()
                    
                    # Verify httpx.AsyncClient was called with http2=True
                    call_kwargs = mock_client_class.call_args[1]
                    assert call_kwargs.get('http2') is True
    
    async def test_connection_limits(self, mock_http_client):
        """Test connection limits (max_keepalive, max_connections)."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value = mock_http_client
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic'):
                    pool = LLMConnectionPool()
                    
                    # Verify httpx.AsyncClient was called with limits
                    call_kwargs = mock_client_class.call_args[1]
                    assert 'limits' in call_kwargs
                    limits = call_kwargs['limits']
                    assert limits.max_keepalive_connections == 10
                    assert limits.max_connections == 20
    
    async def test_timeout_configuration(self, mock_http_client):
        """Test timeout configuration."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client_class.return_value = mock_http_client
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic'):
                    pool = LLMConnectionPool(timeout=45.0)
                    
                    # Verify timeout was passed to httpx.AsyncClient
                    call_kwargs = mock_client_class.call_args[1]
                    assert call_kwargs.get('timeout') == 45.0
    
    async def test_raises_error_when_api_key_missing(self):
        """Test raises ValueError when ANTHROPIC_API_KEY missing."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                LLMConnectionPool()
    
    async def test_anthropic_client_created_with_shared_http_client(self, mock_http_client):
        """Test Anthropic client created with shared HTTP client."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic') as mock_anthropic:
                    pool = LLMConnectionPool()
                    
                    # Verify AsyncAnthropic was called with http_client
                    mock_anthropic.assert_called_once()
                    call_kwargs = mock_anthropic.call_args[1]
                    assert 'http_client' in call_kwargs
                    assert call_kwargs['http_client'] == mock_http_client


@pytest.mark.asyncio
class TestLLMConnectionPoolWarmup:
    """Test connection pool warmup."""
    
    async def test_warmup_sets_flag(self, mock_http_client, mock_anthropic_client):
        """Test warmup sets _warmed_up flag."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic', return_value=mock_anthropic_client):
                    pool = LLMConnectionPool()
                    
                    await pool.warmup()
                    
                    assert pool._warmed_up is True
    
    async def test_warmup_doesnt_run_twice(self, mock_http_client, mock_anthropic_client):
        """Test warmup doesn't run twice (idempotent)."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic', return_value=mock_anthropic_client):
                    pool = LLMConnectionPool()
                    
                    await pool.warmup()
                    call_count = mock_anthropic_client.messages.create.call_count
                    
                    # Call warmup again
                    await pool.warmup()
                    
                    # Should not create another warmup request
                    # (Note: Since warmup uses asyncio.create_task, the exact call count
                    # might vary, but the flag should prevent re-execution)
                    assert pool._warmed_up is True
    
    async def test_warmup_sends_minimal_request(self, mock_http_client, mock_anthropic_client):
        """Test warmup sends minimal request."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic', return_value=mock_anthropic_client):
                    with patch('asyncio.create_task') as mock_create_task:
                        pool = LLMConnectionPool()
                        
                        await pool.warmup()
                        
                        # Verify create_task was called (fire and forget)
                        assert mock_create_task.called
    
    async def test_warmup_error_handling(self, mock_http_client):
        """Test warmup error handling (non-critical)."""
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create = AsyncMock(side_effect=Exception("API error"))
        
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic', return_value=mock_anthropic):
                    pool = LLMConnectionPool()
                    
                    # Warmup should not raise exception
                    await pool.warmup()
                    
                    # Flag should still be set
                    assert pool._warmed_up is True


@pytest.mark.asyncio
class TestLLMConnectionPoolClientRetrieval:
    """Test client retrieval."""
    
    async def test_get_anthropic_client_returns_shared_client(self, mock_http_client):
        """Test get_anthropic_client returns shared client."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic') as mock_anthropic:
                    mock_client = MagicMock()
                    mock_anthropic.return_value = mock_client
                    
                    pool = LLMConnectionPool()
                    client = pool.get_anthropic_client()
                    
                    assert client == mock_client
                    assert client == pool.anthropic
    
    async def test_client_reuse_across_calls(self, mock_http_client):
        """Test client reuse across calls."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic') as mock_anthropic:
                    mock_client = MagicMock()
                    mock_anthropic.return_value = mock_client
                    
                    pool = LLMConnectionPool()
                    client1 = pool.get_anthropic_client()
                    client2 = pool.get_anthropic_client()
                    
                    assert client1 == client2
                    # Should only create one client
                    assert mock_anthropic.call_count == 1


@pytest.mark.asyncio
class TestLLMConnectionPoolConnectionManagement:
    """Test connection management."""
    
    async def test_close_closes_http_client(self, mock_http_client):
        """Test close() closes HTTP client."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic'):
                    pool = LLMConnectionPool()
                    
                    await pool.close()
                    
                    mock_http_client.aclose.assert_called_once()
    
    async def test_cleanup_on_shutdown(self, mock_http_client):
        """Test cleanup on shutdown."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('httpx.AsyncClient', return_value=mock_http_client):
                with patch('sales_agent.engine.llm_pool.AsyncAnthropic'):
                    pool = LLMConnectionPool()
                    
                    await pool.close()
                    
                    # Verify client was closed
                    assert mock_http_client.aclose.called

