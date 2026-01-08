import os
import sys
import json
import logging
from anthropic import AsyncAnthropic, APIError, APIConnectionError, APIStatusError
from typing import Dict, Any, Optional

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config
from .utils import retry_with_backoff

logger = logging.getLogger(__name__)

class SituationDetector:
    def __init__(self, situations: Dict, llm_pool=None, llm_router=None):
        self.situations = situations
        # Use router if provided (Phase 3), otherwise use pool or direct client
        self.router = llm_router
        if llm_router:
            # Router handles multiple providers
            pass
        elif llm_pool:
            self.client = llm_pool.get_anthropic_client()
        else:
            self.client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        # Default fallback situation
        self.default_situation = config.DEFAULT_SITUATION
        # Pre-compute situation keys for compressed prompts
        self.situation_keys = list(self.situations.keys())
    
    async def detect(
        self, 
        message: str, 
        context: Dict,
        complexity: Optional[str] = None
    ) -> Dict[str, Any]:
        
        # Compressed prompt: ~150 tokens vs ~400 tokens original
        context_str = ", ".join([f"{k}:{v}" for k, v in context.items() if v]) or "none"
        situations_str = ", ".join(self.situation_keys)
        
        prompt = f"""Detect situation from message. Return JSON only.
Situations: {situations_str}
Context: {context_str}
Message: "{message}"
Format: {{"situation": "key", "confidence": 0.0-1.0, "stage": "discovery|qualification|presentation|objection_handling|closing"}}
Return ONLY valid JSON."""

        # Use router if available (Phase 3), otherwise fallback to direct client
        try:
            if self.router:
                async def _call_router():
                    response_text, winning_provider = await self.router.call(
                        prompt=prompt,
                        max_tokens=config.LLM_MAX_TOKENS_SITUATION,
                        complexity=complexity or "medium"  # Pass complexity for tiered selection
                    )
                    logger.debug(f"Situation detection: {winning_provider} won the race (complexity: {complexity})")
                    return response_text

                response_text = await retry_with_backoff(
                    _call_router,
                    max_attempts=config.RETRY_MAX_ATTEMPTS,
                    base_delay=config.RETRY_BASE_DELAY_SECONDS,
                    exceptions=(Exception,)
                )
            else:
                # Fallback to direct client (Phase 1/2 behavior)
                async def _call_api():
                    response = await self.client.messages.create(
                        model=config.ANTHROPIC_MODEL,
                        max_tokens=config.LLM_MAX_TOKENS_SITUATION,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text

                response_text = await retry_with_backoff(
                    _call_api,
                    max_attempts=config.RETRY_MAX_ATTEMPTS,
                    base_delay=config.RETRY_BASE_DELAY_SECONDS,
                    exceptions=(APIError, APIConnectionError, APIStatusError, Exception)
                )

            result = json.loads(response_text)

            # Validate situation exists
            if result.get("situation") not in self.situations:
                logger.warning(f"Unknown situation detected: {result.get('situation')}. Using default.")
                result["situation"] = self.default_situation
                result["confidence"] = config.DEFAULT_CONFIDENCE

            return result

        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            logger.error(f"Failed to parse situation detection response: {str(e)}")
            # Return default fallback
            return {
                "situation": self.default_situation,
                "confidence": config.DEFAULT_CONFIDENCE,
                "stage": config.DEFAULT_STAGE
            }
        except Exception as e:
            logger.error(f"Unexpected error in situation detection: {str(e)}")
            # Return default fallback
            return {
                "situation": self.default_situation,
                "confidence": config.DEFAULT_CONFIDENCE,
                "stage": config.DEFAULT_STAGE
            }
    
    def _format_situations(self) -> str:
        formatted = []
        for key, config in self.situations.items():
            signals = ", ".join(config.get("signals", [])[:3])
            formatted.append(f"- {key}: signals=[{signals}]")
        return "\n".join(formatted)

