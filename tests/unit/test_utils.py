"""
Unit tests for utils module.

Tests retry logic with exponential backoff.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from sales_agent.engine.utils import retry_with_backoff


@pytest.mark.asyncio
class TestRetryWithBackoff:
    """Test retry logic with exponential backoff."""
    
    async def test_successful_call_on_first_attempt(self):
        """Test successful call on first attempt (no retry needed)."""
        func = AsyncMock(return_value="success")
        
        result = await retry_with_backoff(func, max_attempts=3)
        
        assert result == "success"
        assert func.call_count == 1
    
    async def test_successful_call_after_retry(self):
        """Test successful call after retry."""
        func = AsyncMock(side_effect=[Exception("fail"), Exception("fail"), "success"])
        
        result = await retry_with_backoff(func, max_attempts=3, base_delay=0.01)
        
        assert result == "success"
        assert func.call_count == 3
    
    async def test_all_attempts_fail(self):
        """Test all attempts fail (raises last exception)."""
        func = AsyncMock(side_effect=Exception("always fail"))
        
        with pytest.raises(Exception, match="always fail"):
            await retry_with_backoff(func, max_attempts=3, base_delay=0.01)
        
        assert func.call_count == 3
    
    async def test_exponential_backoff_delay(self):
        """Test exponential backoff delay calculation."""
        func = AsyncMock(side_effect=[Exception("fail"), "success"])
        
        with patch('asyncio.sleep') as mock_sleep:
            await retry_with_backoff(func, max_attempts=3, base_delay=1.0, max_delay=10.0)
            
            # Should have slept once (after first failure)
            assert mock_sleep.call_count == 1
            # Delay should be base_delay * (2 ** attempt) = 1.0 * (2 ** 0) = 1.0
            mock_sleep.assert_called_once_with(1.0)
    
    async def test_backoff_delay_progression(self):
        """Test backoff delay progression: 1s, 2s, 4s."""
        func = AsyncMock(side_effect=[Exception("fail"), Exception("fail"), Exception("fail")])
        
        with patch('asyncio.sleep') as mock_sleep:
            with pytest.raises(Exception):
                await retry_with_backoff(func, max_attempts=3, base_delay=1.0, max_delay=10.0)
            
            # Should have slept twice (after first and second failures)
            assert mock_sleep.call_count == 2
            # First delay: base_delay * (2 ** 0) = 1.0
            # Second delay: base_delay * (2 ** 1) = 2.0
            assert mock_sleep.call_args_list[0][0][0] == 1.0
            assert mock_sleep.call_args_list[1][0][0] == 2.0
    
    async def test_max_delay_cap(self):
        """Test max_delay cap prevents excessive delays."""
        func = AsyncMock(side_effect=[Exception("fail"), Exception("fail"), Exception("fail")])
        
        with patch('asyncio.sleep') as mock_sleep:
            with pytest.raises(Exception):
                await retry_with_backoff(func, max_attempts=3, base_delay=10.0, max_delay=15.0)
            
            # Should have slept twice
            assert mock_sleep.call_count == 2
            # First delay: min(10.0 * (2 ** 0), 15.0) = min(10.0, 15.0) = 10.0
            # Second delay: min(10.0 * (2 ** 1), 15.0) = min(20.0, 15.0) = 15.0 (capped)
            assert mock_sleep.call_args_list[0][0][0] == 10.0
            assert mock_sleep.call_args_list[1][0][0] == 15.0
    
    async def test_specific_exception_types_caught(self):
        """Test specific exception types are caught and retried."""
        class CustomException(Exception):
            pass
        
        func = AsyncMock(side_effect=[CustomException("fail"), "success"])
        
        result = await retry_with_backoff(
            func, 
            max_attempts=3, 
            base_delay=0.01,
            exceptions=(CustomException,)
        )
        
        assert result == "success"
        assert func.call_count == 2
    
    async def test_other_exception_types_not_retried(self):
        """Test other exception types are not retried."""
        class CustomException(Exception):
            pass
        
        class OtherException(Exception):
            pass
        
        func = AsyncMock(side_effect=OtherException("don't retry"))
        
        with pytest.raises(OtherException):
            await retry_with_backoff(
                func, 
                max_attempts=3, 
                base_delay=0.01,
                exceptions=(CustomException,)
            )
        
        # Should only be called once (not retried)
        assert func.call_count == 1
    
    async def test_correct_number_of_attempts(self):
        """Test correct number of attempts (max_attempts)."""
        func = AsyncMock(side_effect=Exception("fail"))
        
        with pytest.raises(Exception):
            await retry_with_backoff(func, max_attempts=5, base_delay=0.01)
        
        assert func.call_count == 5
    
    async def test_no_retry_when_max_attempts_is_one(self):
        """Test no retry when max_attempts is 1."""
        func = AsyncMock(side_effect=Exception("fail"))
        
        with pytest.raises(Exception):
            await retry_with_backoff(func, max_attempts=1, base_delay=0.01)
        
        assert func.call_count == 1
    
    async def test_default_parameters(self):
        """Test default parameters work correctly."""
        func = AsyncMock(return_value="success")
        
        result = await retry_with_backoff(func)
        
        assert result == "success"
        assert func.call_count == 1
    
    async def test_last_exception_raised(self):
        """Test last exception is raised after all attempts fail."""
        exception1 = Exception("first")
        exception2 = Exception("second")
        exception3 = Exception("third")
        
        func = AsyncMock(side_effect=[exception1, exception2, exception3])
        
        with pytest.raises(Exception) as exc_info:
            await retry_with_backoff(func, max_attempts=3, base_delay=0.01)
        
        # Should raise the last exception
        assert exc_info.value == exception3

