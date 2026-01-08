import os
import sys
import json
import logging
from anthropic import AsyncAnthropic, APIError, APIConnectionError, APIStatusError
from typing import Dict, Any, List, Optional

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config
from .utils import retry_with_backoff

logger = logging.getLogger(__name__)

class CaptureEngine:
    def __init__(self, capture_schema: Dict, llm_pool=None, llm_router=None):
        self.schema = capture_schema
        # Use router if provided (Phase 3), otherwise use pool or direct client
        self.router = llm_router
        if llm_router:
            # Router handles multiple providers
            pass
        elif llm_pool:
            self.client = llm_pool.get_anthropic_client()
        else:
            self.client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        self.slots = capture_schema["capture_schema"]["slots"]
        # Pre-compute slot names for compressed prompts
        self.slot_names = list(self.slots.keys())
    
    async def extract(
        self, 
        message: str, 
        existing_context: Dict,
        complexity: Optional[str] = None
    ) -> Dict[str, Any]:
        
        # Compressed prompt: ~150 tokens vs ~500 tokens original
        context_str = ", ".join([f"{k}:{v}" for k, v in existing_context.items() if v]) or "none"
        slot_names_str = ", ".join(self.slot_names)
        
        prompt = f"""Extract slots from message. Return JSON only.
Slots: {slot_names_str}
Context: {context_str}
Message: "{message}"
Format: {{"slots": {{"slot": "value"}}, "new_quotes": ["quote"]}}
Extract verbatim quotes. Return ONLY valid JSON."""

        # Use router if available (Phase 3), otherwise fallback to direct client
        if self.router:
            async def _call_router():
                response_text, winning_provider = await self.router.call(
                    prompt=prompt,
                    max_tokens=config.LLM_MAX_TOKENS_CAPTURE,
                    complexity=complexity or "medium"  # Pass complexity for tiered selection
                )
                logger.debug(f"Capture: {winning_provider} won the race (complexity: {complexity})")
                return response_text
            
            try:
                response_text = await retry_with_backoff(
                    _call_router,
                    max_attempts=config.RETRY_MAX_ATTEMPTS,
                    base_delay=config.RETRY_BASE_DELAY_SECONDS,
                    exceptions=(Exception,)
                )
            except Exception as e:
                logger.error(f"Router call failed in capture: {str(e)}")
                # Fallback to empty result
                return {
                    "slots": {},
                    "new_quotes": []
                }
        else:
            # Fallback to direct client (Phase 1/2 behavior)
            async def _call_api():
                response = await self.client.messages.create(
                    model=config.ANTHROPIC_MODEL,
                    max_tokens=config.LLM_MAX_TOKENS_CAPTURE,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            
            try:
                response_text = await retry_with_backoff(
                    _call_api,
                    max_attempts=config.RETRY_MAX_ATTEMPTS,
                    base_delay=config.RETRY_BASE_DELAY_SECONDS,
                    exceptions=(APIError, APIConnectionError, APIStatusError, Exception)
                )
                
                result = json.loads(response_text)
                
                # Filter out nulls
                result["slots"] = {k: v for k, v in result["slots"].items() if v}
                
                return result
                
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logger.error(f"Failed to parse capture response: {str(e)}")
                # Return empty result as fallback
                return {
                    "slots": {},
                    "new_quotes": []
                }
            except Exception as e:
                logger.error(f"Unexpected error in capture: {str(e)}")
                # Return empty result as fallback
                return {
                    "slots": {},
                    "new_quotes": []
                }
    
    def _format_slots(self) -> str:
        formatted = []
        for name, config in self.slots.items():
            formatted.append(f"- {name}: {config['description']}")
            listen_for_list = config['listen_for'][:5] if len(config['listen_for']) > 5 else config['listen_for']
            formatted.append(f"  Listen for: {', '.join(listen_for_list)}...")
        return "\n".join(formatted)

