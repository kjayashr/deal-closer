import os
import sys
import re
import logging
from anthropic import AsyncAnthropic, APIError, APIConnectionError, APIStatusError
from typing import Dict, Any, List, Optional

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config
from .utils import retry_with_backoff

logger = logging.getLogger(__name__)

class ResponseGenerator:
    def __init__(self, principles: List[Dict], llm_pool=None, llm_router=None):
        self.principles = {p["principle_id"]: p for p in principles}
        # Use router if provided (Phase 3), otherwise use pool or direct client
        self.router = llm_router
        if llm_router:
            # Router handles multiple providers
            pass
        elif llm_pool:
            self.client = llm_pool.get_anthropic_client()
        else:
            self.client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        # Cache for formatted principle strings to reduce prompt building time
        self._principle_cache: Dict[str, str] = {}
    
    def _format_principle_section(self, principle: Dict) -> str:
        """Format principle section, using cache if available."""
        principle_id = principle.get("principle_id")
        if principle_id and principle_id in self._principle_cache:
            return self._principle_cache[principle_id]
        
        formatted = f"""Name: {principle['name']}
Definition: {principle['definition']}
Mechanism: {principle['mechanism']}
Intervention: {principle['intervention']}"""
        
        if principle_id:
            self._principle_cache[principle_id] = formatted
        
        return formatted
    
    async def generate(
        self,
        principle: Dict,
        customer_quotes: List[str],
        situation: str,
        context: Dict,
        product_context: Dict = None,
        complexity: Optional[str] = None
    ) -> Dict[str, Any]:
        
        # Compressed prompt: ~200 tokens vs ~600 tokens original
        principle_name = principle.get('name', '')
        principle_intervention = principle.get('intervention', '')
        quotes_str = " | ".join(customer_quotes[-config.RESPONSE_QUOTES_FOR_PROMPT:]) if customer_quotes else "none"
        pain = context.get('pain', '') or 'none'
        product_info = str(product_context) if product_context else 'none'
        
        prompt = f"""Generate natural sales response. MAX 2 sentences.
Principle: {principle_name} - {principle_intervention}
Quotes: {quotes_str}
Situation: {situation} | Pain: {pain} | Product: {product_info}
Rules: Use exact words back, acknowledge concern first, sound casual, no bullets, no jargon.
Response:"""

        # Use router if available (Phase 3), otherwise fallback to direct client
        if self.router:
            async def _call_router():
                response_text, winning_provider = await self.router.call(
                    prompt=prompt,
                    max_tokens=config.LLM_MAX_TOKENS_RESPONSE,
                    complexity=complexity or "medium"  # Pass complexity for tiered selection
                )
                logger.debug(f"Response generation: {winning_provider} won the race (complexity: {complexity})")
                return response_text
            
            try:
                response_text = await retry_with_backoff(
                    _call_router,
                    max_attempts=config.RETRY_MAX_ATTEMPTS,
                    base_delay=config.RETRY_BASE_DELAY_SECONDS,
                    exceptions=(Exception,)
                )
            except Exception as e:
                logger.error(f"Router call failed in response generation: {str(e)}")
                # Fallback to simple response
                fallback = self._generate_fallback_response(customer_quotes, situation)
                return {
                    "response": fallback,
                    "principle_used": principle["name"]
                }
        else:
            # Fallback to direct client (Phase 1/2 behavior)
            async def _call_api():
                response = await self.client.messages.create(
                    model=config.ANTHROPIC_MODEL,
                    max_tokens=config.LLM_MAX_TOKENS_RESPONSE,
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
            
            # Validate and enforce 2-sentence limit
            validated_response = self._validate_sentence_count(response_text.strip())
            
            return {
                "response": validated_response,
                "principle_used": principle["name"]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            # Generate fallback response using customer quotes
            fallback = self._generate_fallback_response(customer_quotes, situation)
            return {
                "response": fallback,
                "principle_used": principle["name"]
            }
    
    def _generate_fallback_response(self, customer_quotes: List[str], situation: str) -> str:
        """Generate a simple fallback response when LLM fails."""
        if customer_quotes:
            quote = customer_quotes[-1]
            return f"I understand you mentioned '{quote}'. Can you tell me more about what you're looking for?"
        return "I'd like to help you find the right product. What brings you in today?"
    
    def _format_quotes(self, quotes: List[str]) -> str:
        if not quotes:
            return "- No quotes captured yet"
        return "\n".join([f'- "{q}"' for q in quotes])
    
    def _validate_sentence_count(self, text: str) -> str:
        """
        Validate that response has max N sentences. If more, truncate to first N.
        """
        # Split by sentence endings (. ! ?) - this pattern captures sentence boundaries
        # Pattern: sentence ending followed by space or end of string
        sentence_pattern = r'([^.!?]*[.!?]+)'
        matches = re.findall(sentence_pattern, text)
        
        # Filter out empty matches
        sentences = [s.strip() for s in matches if s.strip()]
        
        # If we have more than max sentences, truncate to first N
        if len(sentences) > config.RESPONSE_MAX_SENTENCES:
            logger.warning(f"Response exceeded {config.RESPONSE_MAX_SENTENCES} sentences ({len(sentences)}). Truncating to first {config.RESPONSE_MAX_SENTENCES}.")
            return " ".join(sentences[:config.RESPONSE_MAX_SENTENCES])
        
        # If no sentences found (edge case), return original text
        if not sentences:
            return text
        
        return text

