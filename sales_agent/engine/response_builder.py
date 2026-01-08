"""
Response Builder - Structures responses with customer_facing and agent_dashboard
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class ResponseBuilder:
    def __init__(self, principles: Dict[str, Dict], capture_schema: Dict):
        self.principles = principles
        self.capture_schema = capture_schema
        self.slots = capture_schema.get("capture_schema", {}).get("slots", {})
    
    def build(
        self,
        customer_message: str,
        customer_facing_response: str,
        detection_result: Dict[str, Any],
        captured_context: Dict[str, Any],
        captured_quotes: List[str],
        recommendation: Dict[str, Any],
        fallback_principle: Dict[str, Any],
        session_id: str,
        turn_count: int,
        resistance_count: int,
        principles_used: List[str],
        latency_ms: int,
        step_latencies: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Build the complete response structure with customer_facing and agent_dashboard.
        """
        
        # Detect persona
        persona_result = self._detect_persona(
            customer_message=customer_message,
            situation=detection_result.get("situation", ""),
            context=captured_context
        )
        
        # Build qualification checklist
        qualification_checklist = self._build_qualification_checklist(captured_context)
        
        # Determine next probe
        next_probe = self._determine_next_probe(captured_context, qualification_checklist)
        
        # Format recommendation with full details
        recommendation_formatted = self._format_recommendation(recommendation)
        
        # Format fallback with response
        fallback_formatted = self._format_fallback(fallback_principle, captured_quotes)
        
        return {
            "customer_facing": {
                "response": customer_facing_response
            },
            "agent_dashboard": {
                "detection": {
                    "customer_said": customer_message,
                    "detected_situation": detection_result.get("situation", "unknown"),
                    "situation_confidence": detection_result.get("confidence", 0.0),
                    "micro_stage": detection_result.get("stage", "discovery"),
                    "detected_persona": persona_result.get("persona", "unknown"),
                    "persona_confidence": persona_result.get("confidence", 0.0)
                },
                "captured_context": captured_context,
                "captured_quotes": captured_quotes,
                "qualification_checklist": qualification_checklist,
                "recommendation": recommendation_formatted,
                "fallback": fallback_formatted,
                "next_probe": next_probe,
                "session": {
                    "session_id": session_id,
                    "turn_count": turn_count,
                    "resistance_count": resistance_count,
                    "principles_used": principles_used
                },
                "system": {
                    "latency_ms": latency_ms,
                    "step_latencies": step_latencies or {}
                }
            }
        }
    
    def _detect_persona(
        self,
        customer_message: str,
        situation: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect customer persona based on message, situation, and context.
        """
        message_lower = customer_message.lower()
        
        # Price-conscious persona
        price_signals = [
            "expensive", "too much", "cost", "price", "afford", "budget",
            "cheaper", "discount", "deal", "sale", "emi", "installment"
        ]
        has_price_signal = any(signal in message_lower for signal in price_signals)
        is_price_situation = situation in [
            "price_shock_in_store", "budget_boundary", "discount_expectation",
            "online_price_checking", "cash_vs_card_decision"
        ]
        
        if has_price_signal or is_price_situation or context.get("budget_signal"):
            return {
                "persona": "price_conscious",
                "confidence": 0.85 if (has_price_signal and is_price_situation) else 0.70
            }
        
        # Research-oriented persona
        research_signals = [
            "research", "compare", "check", "review", "read about", "learn more",
            "information", "specs", "features", "options"
        ]
        has_research_signal = any(signal in message_lower for signal in research_signals)
        is_research_situation = situation in [
            "want_to_research_more", "feature_overload_paralysis", "upgrade_value_uncertainty"
        ]
        
        if has_research_signal or is_research_situation:
            return {
                "persona": "research_oriented",
                "confidence": 0.80 if (has_research_signal and is_research_situation) else 0.65
            }
        
        # Risk-averse persona
        risk_signals = [
            "warranty", "return", "guarantee", "what if", "worried", "concerned",
            "risk", "safe", "reliable", "trust", "service", "repair"
        ]
        has_risk_signal = any(signal in message_lower for signal in risk_signals)
        is_risk_situation = situation in [
            "warranty_and_service_concern", "return_policy_anxiety",
            "after_sales_support_worry", "past_purchase_regret"
        ]
        
        if has_risk_signal or is_risk_situation:
            return {
                "persona": "risk_averse",
                "confidence": 0.80 if (has_risk_signal and is_risk_situation) else 0.65
            }
        
        # Ready-to-buy persona
        ready_signals = [
            "ready", "buy", "take it", "purchase", "order", "delivery",
            "when can i", "how do i pay", "let's do it"
        ]
        has_ready_signal = any(signal in message_lower for signal in ready_signals)
        is_ready_situation = situation in [
            "second_visit_return", "stock_availability_check", "delivery_timeline_concern"
        ]
        
        if has_ready_signal or is_ready_situation:
            return {
                "persona": "ready_to_buy",
                "confidence": 0.85 if (has_ready_signal and is_ready_situation) else 0.70
            }
        
        # Default: exploratory
        return {
            "persona": "exploratory",
            "confidence": 0.60
        }
    
    def _build_qualification_checklist(self, context: Dict[str, Any]) -> Dict[str, bool]:
        """
        Build qualification checklist based on captured context.
        """
        return {
            "need_identified": bool(context.get("pain") or context.get("trigger_event") or context.get("current_state")),
            "pain_expressed": bool(context.get("pain")),
            "product_interest": bool(context.get("product_interest") or context.get("product_model")),
            "budget_discussed": bool(context.get("budget_signal") or context.get("budget_range") or context.get("payment_preference")),
            "timeline_known": bool(context.get("timeline") or context.get("urgency") or context.get("trigger_event")),
            "decision_maker_known": bool(context.get("decision_maker") or context.get("buying_authority") or not context.get("need_to_check_with_family"))
        }
    
    def _determine_next_probe(
        self,
        context: Dict[str, Any],
        qualification_checklist: Dict[str, bool]
    ) -> Dict[str, str]:
        """
        Determine the next question to ask based on missing qualification slots.
        Priority order: pain > timeline > budget > decision_maker > product_interest
        """
        
        # Priority order for probing
        probe_priority = [
            ("pain", "What problem are you trying to solve?"),
            ("timeline", "When were you hoping to get this sorted?"),
            ("budget", "What's your budget range for this?"),
            ("decision_maker", "Are you the one making the decision, or do you need to check with someone?"),
            ("product_interest", "What features are most important to you?")
        ]
        
        # Map checklist to probe targets
        checklist_to_probe = {
            "pain_expressed": "pain",
            "timeline_known": "timeline",
            "budget_discussed": "budget",
            "decision_maker_known": "decision_maker",
            "product_interest": "product_interest"
        }
        
        # Find first missing high-priority item
        for checklist_key, probe_target in checklist_to_probe.items():
            if not qualification_checklist.get(checklist_key, False):
                # Find the question for this target
                for target, question in probe_priority:
                    if target == probe_target:
                        return {
                            "target": target,
                            "question": question
                        }
        
        # If all are filled, probe for deeper context
        if not context.get("duration"):
            return {
                "target": "duration",
                "question": "How long have you been dealing with this?"
            }
        
        if not context.get("current_state"):
            return {
                "target": "current_state",
                "question": "What are you currently using?"
            }
        
        # Default: move toward close
        return {
            "target": "commitment",
            "question": "What would it take for you to feel confident about this purchase?"
        }
    
    def _format_recommendation(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the recommendation with principle details.
        """
        principle = recommendation.get("principle", {})
        principle_id = principle.get("principle_id", "")
        
        # Get source information
        source = principle.get("source", {})
        source_str = "Unknown"
        if isinstance(source, dict):
            author = source.get("author", "")
            book = source.get("book", "")
            chapter = source.get("chapter", "")
            page = source.get("page", "")
            if author and book:
                source_str = f"{author}, {book}"
                if chapter:
                    source_str += f", Ch.{chapter}"
                if page:
                    source_str += f", p.{page}"
        elif isinstance(source, str):
            source_str = source
        
        return {
            "principle": principle.get("name", "Unknown"),
            "principle_id": principle_id,
            "source": source_str,
            "approach": principle.get("intervention", ""),
            "response": recommendation.get("response", ""),  # This will be set by orchestrator
            "why_it_works": principle.get("mechanism", "")
        }
    
    def _format_fallback(
        self,
        fallback_principle: Dict[str, Any],
        captured_quotes: List[str]
    ) -> Dict[str, Any]:
        """
        Format the fallback principle with a sample response.
        """
        principle_id = fallback_principle.get("principle_id", "")
        principle_name = fallback_principle.get("name", "Unknown")
        
        # Generate a simple fallback response
        if captured_quotes:
            last_quote = captured_quotes[-1]
            fallback_response = f"I understand you mentioned '{last_quote}'. Can you tell me more about what you're looking for?"
        else:
            fallback_response = "I'd like to help you find the right product. What brings you in today?"
        
        return {
            "principle": principle_name,
            "principle_id": principle_id,
            "response": fallback_response
        }

