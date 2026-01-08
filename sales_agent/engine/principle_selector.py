from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class PrincipleSelector:
    def __init__(self, selector_rules: Dict, principles: List[Dict]):
        self.rules = selector_rules["principle_selector"]["rules"]
        self.fallback = selector_rules["principle_selector"]["fallback"]
        self.principles = {p["principle_id"]: p for p in principles}
        
        # Mapping from rule situation names to actual situation keys
        self.situation_mapping = {
            "price_objection": "price_shock_in_store",
            "comparing_online": "online_price_checking",
            "need_to_ask_spouse": "need_to_check_with_family",
            "warranty_concern": "warranty_and_service_concern",
            "past_bad_experience": "past_purchase_regret",
            "wants_discount": "discount_expectation",
            "will_come_back_later": "walking_away_pause",
            "let_me_think": "urgency_without_commitment",
            "ready_to_buy": "second_visit_return",
            "asking_about_stock": "stock_availability_check",
            "asking_about_delivery": "delivery_timeline_concern",
            "saw_bad_reviews": "authenticity_genuineness_doubt",
            "skeptical_about_quality": "quality_doubt",
            "looking_for_cheaper": "budget_boundary",
            "asking_about_emi": "cash_vs_card_decision",
            "comparing_models": "upgrade_value_uncertainty",
            "doing_research": "want_to_research_more",
            "service_concern": "after_sales_support_worry",
            "return_policy_question": "return_policy_anxiety",
            "friend_had_issues": "conflicting_peer_recommendation",
            "confused_about_features": "feature_overload_paralysis",
            "just_browsing": "just_browsing"
        }
    
    def _normalize_situation(self, situation: str) -> str:
        """Map situation from rule name to actual situation key, or return as-is if already correct."""
        # First check if it's already a valid situation key (no mapping needed)
        if situation in self.situation_mapping.values():
            return situation
        # Otherwise, try to map it
        return self.situation_mapping.get(situation, situation)
    
    def select(
        self,
        situation: str,
        context: Dict,
        principle_history: List[str],
        resistance_count: int
    ) -> Dict[str, Any]:
        
        # Normalize situation name (map from rule name to actual situation key)
        normalized_situation = self._normalize_situation(situation)
        
        # Check fallback conditions
        if resistance_count >= 2:
            principle_id = self.fallback.get("after_failed_attempt_2", self.fallback["default"])
            return {
                "principle": self.principles[principle_id],
                "reason": "fallback_after_resistance_2"
            }
        elif resistance_count >= 1:
            principle_id = self.fallback.get("after_failed_attempt_1", self.fallback["default"])
            return {
                "principle": self.principles[principle_id],
                "reason": "fallback_after_resistance_1"
            }
        
        # Check if no context available
        if not context:
            principle_id = self.fallback.get("when_no_context", self.fallback["default"])
            return {
                "principle": self.principles[principle_id],
                "reason": "fallback_no_context"
            }
        
        # Find matching rules - normalize both the incoming situation and rule situations
        for rule in self.rules:
            rule_situation = rule["situation"]
            # Normalize the rule situation to actual situation key
            normalized_rule_situation = self._normalize_situation(rule_situation)
            
            # Match if normalized situations match
            if normalized_rule_situation != normalized_situation:
                continue
            
            # Check context conditions
            if self._check_conditions(rule, context):
                principle_id = rule["use"]
                
                # Validate principle exists
                if principle_id not in self.principles:
                    logger.warning(f"Principle {principle_id} not found, skipping rule")
                    continue
                
                # Avoid repeating same principle
                if self._count_recent_uses(principle_id, principle_history) >= 2:
                    continue
                
                return {
                    "principle": self.principles[principle_id],
                    "reason": f"rule_match: {rule.get('note', 'direct match')}"
                }
        
        # No match - use fallback
        principle_id = self.fallback["default"]
        if principle_id not in self.principles:
            logger.error(f"Fallback principle {principle_id} not found!")
            # Use first available principle as last resort
            principle_id = list(self.principles.keys())[0] if self.principles else None
            if not principle_id:
                raise ValueError("No principles available!")
        
        return {
            "principle": self.principles[principle_id],
            "reason": "no_rule_match"
        }
    
    def _check_conditions(self, rule: Dict, context: Dict) -> bool:
        # Check "when_context_has"
        if "when_context_has" in rule:
            for required in rule["when_context_has"]:
                if required not in context or not context[required]:
                    return False
        
        # Check "when_context_missing"
        if "when_context_missing" in rule:
            for forbidden in rule["when_context_missing"]:
                if forbidden in context and context[forbidden]:
                    return False
        
        return True
    
    def _count_recent_uses(self, principle_id: str, history: List[str], window: int = 3) -> int:
        recent = history[-window:] if len(history) >= window else history
        return recent.count(principle_id)
    
    def get_fallback_principle(
        self,
        resistance_count: int = 0,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        Get the fallback principle based on current state.
        """
        if resistance_count >= 2:
            principle_id = self.fallback.get("after_failed_attempt_2", self.fallback["default"])
        elif resistance_count >= 1:
            principle_id = self.fallback.get("after_failed_attempt_1", self.fallback["default"])
        elif not context:
            principle_id = self.fallback.get("when_no_context", self.fallback["default"])
        else:
            principle_id = self.fallback["default"]
        
        if principle_id not in self.principles:
            logger.error(f"Fallback principle {principle_id} not found!")
            principle_id = list(self.principles.keys())[0] if self.principles else None
            if not principle_id:
                raise ValueError("No principles available!")
        
        return self.principles[principle_id]

