"""
LLM Router with multi-provider racing support.
Races multiple LLM providers and returns the first completed response.
"""
import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from anthropic import AsyncAnthropic, APIError, APIConnectionError, APIStatusError
from openai import AsyncOpenAI

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config

logger = logging.getLogger(__name__)


class LLMRouter:
    """Router that races multiple LLM providers and returns the first completed response."""
    
    def __init__(self, llm_pool=None, enable_openai: bool = True):
        """
        Initialize LLM Router with multiple providers.
        
        Args:
            llm_pool: Optional LLMConnectionPool (uses shared Anthropic client)
            enable_openai: Whether to enable OpenAI racing (default: True)
        """
        # Anthropic client (from pool if available)
        if llm_pool:
            self.anthropic_client = llm_pool.get_anthropic_client()
        else:
            api_key = config.ANTHROPIC_API_KEY
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")
            self.anthropic_client = AsyncAnthropic(api_key=api_key)
        
        # OpenAI client (if enabled)
        self.openai_enabled = enable_openai
        self.openai_client = None
        
        if self.openai_enabled:
            openai_key = config.OPENAI_API_KEY
            if openai_key:
                self.openai_client = AsyncOpenAI(api_key=openai_key)
            else:
                logger.warning("OPENAI_API_KEY not set, OpenAI racing disabled")
                self.openai_enabled = False
        
        # Provider statistics
        self.stats = {
            "anthropic": {"wins": 0, "errors": 0, "total": 0},
            "openai": {"wins": 0, "errors": 0, "total": 0}
        }
    
    async def call(
        self,
        prompt: str,
        max_tokens: int = 500,
        model_config: Optional[Dict[str, str]] = None,
        complexity: str = "medium"
    ) -> Tuple[str, str]:
        """
        Call LLM with racing - returns first completed response.
        Uses tiered model selection based on complexity.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens to generate
            model_config: Optional dict with model overrides (anthropic_model, openai_model)
            complexity: Complexity level ("simple", "medium", "complex") for tiered selection
        
        Returns:
            Tuple of (response_text, winning_provider)
        """
        # Tiered model selection based on complexity
        if complexity == "simple":
            # Use fast models for simple queries
            anthropic_model = (model_config or {}).get("anthropic_model", config.ANTHROPIC_MODEL_FAST)
            openai_model = (model_config or {}).get("openai_model", config.OPENAI_MODEL_FAST)
        elif complexity == "complex":
            # Use powerful models for complex queries
            anthropic_model = (model_config or {}).get("anthropic_model", config.ANTHROPIC_MODEL)
            openai_model = (model_config or {}).get("openai_model", config.OPENAI_MODEL)
        else:
            # Medium complexity: use default models (balanced)
            anthropic_model = (model_config or {}).get("anthropic_model", config.ANTHROPIC_MODEL)
            openai_model = (model_config or {}).get("openai_model", config.OPENAI_MODEL)
        
        # Build list of racing coroutines
        coros = []
        task_providers = []
        
        # Anthropic coroutine (always included)
        anthropic_coro = self._call_anthropic(prompt, max_tokens, anthropic_model)
        coros.append(anthropic_coro)
        task_providers.append("anthropic")
        
        # OpenAI coroutine (if enabled)
        if self.openai_enabled and self.openai_client:
            openai_coro = self._call_openai(prompt, max_tokens, openai_model)
            coros.append(openai_coro)
            task_providers.append("openai")
        
        # Race multiple providers (or use single if only one enabled)
        if len(coros) == 1:
            # Single provider case (OpenAI disabled or unavailable)
            try:
                result = await coros[0]
                provider = task_providers[0]
                self.stats[provider]["wins"] += 1
                self.stats[provider]["total"] += 1
                return result, provider
            except Exception as e:
                provider = task_providers[0]
                self.stats[provider]["errors"] += 1
                self.stats[provider]["total"] += 1
                logger.error(f"Single provider ({provider}) failed: {str(e)}")
                raise
        
        # Race multiple providers
        # Convert coroutines to Tasks explicitly to satisfy asyncio APIs
        tasks = [asyncio.create_task(c) for c in coros]
        return await self._race_providers(tasks, task_providers)
    
    async def _race_providers(
        self,
        tasks: List[asyncio.Task],
        providers: List[str]
    ) -> Tuple[str, str]:
        """
        Race multiple providers and return the first completed response.
        Cancels losing tasks.
        
        Args:
            tasks: List of asyncio tasks for each provider
            providers: List of provider names corresponding to tasks
        
        Returns:
            Tuple of (response_text, winning_provider)
        """
        # Wait for first completed task
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Get the winning result
        winning_task = done.pop()
        winning_index = tasks.index(winning_task)
        winning_provider = providers[winning_index]
        
        try:
            result = await winning_task
            self.stats[winning_provider]["wins"] += 1
            self.stats[winning_provider]["total"] += 1
            
            # Cancel all pending tasks
            for task in pending:
                task.cancel()
                # Wait for cancellation to complete (fire and forget)
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    # Log but don't fail - cancellation errors are expected
                    logger.debug(f"Task cancellation completed: {str(e)}")
            
            logger.debug(f"Provider race won by: {winning_provider}")
            return result, winning_provider
            
        except Exception as e:
            # Winning provider failed, try fallback
            self.stats[winning_provider]["errors"] += 1
            self.stats[winning_provider]["total"] += 1
            logger.warning(f"Winning provider ({winning_provider}) failed: {str(e)}")
            
            # Cancel the failed winning task
            winning_task.cancel()
            
            # Try fallback providers
            if pending:
                logger.info(f"Falling back to remaining providers: {[providers[tasks.index(t)] for t in pending]}")
                return await self._fallback_to_remaining(pending, tasks, providers)
            
            # No fallback available
            raise
    
    async def _fallback_to_remaining(
        self,
        pending: set,
        tasks: List[asyncio.Task],
        providers: List[str]
    ) -> Tuple[str, str]:
        """
        Fallback to remaining providers when winner fails.
        
        Args:
            pending: Set of pending tasks
            tasks: All tasks list
            providers: Provider names list
        
        Returns:
            Tuple of (response_text, winning_provider)
        """
        for task in pending:
            provider = providers[tasks.index(task)]
            try:
                result = await task
                self.stats[provider]["wins"] += 1
                self.stats[provider]["total"] += 1
                
                # Cancel remaining pending tasks
                for remaining_task in pending:
                    if remaining_task != task:
                        remaining_task.cancel()
                        try:
                            await remaining_task
                        except (asyncio.CancelledError, Exception):
                            pass
                
                logger.info(f"Fallback provider ({provider}) succeeded")
                return result, provider
                
            except Exception as e:
                self.stats[provider]["errors"] += 1
                self.stats[provider]["total"] += 1
                logger.error(f"Fallback provider ({provider}) failed: {str(e)}")
                continue
        
        # All providers failed
        raise Exception("All LLM providers failed")
    
    async def _call_anthropic(self, prompt: str, max_tokens: int, model: str) -> str:
        """Call Anthropic API."""
        try:
            response = await self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except (APIError, APIConnectionError, APIStatusError) as e:
            logger.debug(f"Anthropic API error: {str(e)}")
            raise
    
    async def _call_openai(self, prompt: str, max_tokens: int, model: str) -> str:
        """Call OpenAI API."""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.debug(f"OpenAI API error: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        stats = {}
        for provider, data in self.stats.items():
            total = data["total"]
            if total > 0:
                stats[provider] = {
                    "wins": data["wins"],
                    "errors": data["errors"],
                    "total": total,
                    "win_rate": data["wins"] / total,
                    "error_rate": data["errors"] / total
                }
            else:
                stats[provider] = {
                    "wins": 0,
                    "errors": 0,
                    "total": 0,
                    "win_rate": 0.0,
                    "error_rate": 0.0
                }
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        for provider in self.stats:
            self.stats[provider] = {"wins": 0, "errors": 0, "total": 0}

