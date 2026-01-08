"""
Unit tests for PrincipleSelector.

Tests rule matching, fallback logic, situation normalization, and principle repetition prevention.
"""
import pytest
from sales_agent.engine.principle_selector import PrincipleSelector


@pytest.fixture
def sample_selector_rules():
    """Sample selector rules for testing."""
    return {
        "principle_selector": {
            "version": "1.0",
            "domain": "retail",
            "rules": [
                {
                    "situation": "price_objection",
                    "when_context_has": ["pain"],
                    "use": "kahneman_loss_aversion_01"
                },
                {
                    "situation": "price_objection",
                    "when_context_missing": ["pain"],
                    "use": "voss_labeling_01",
                    "note": "Uncover pain first"
                },
                {
                    "situation": "comparing_online",
                    "use": "cialdini_authority_01",
                    "note": "Establish in-store value and trust"
                },
                {
                    "situation": "warranty_concern",
                    "use": "kahneman_certainty_effect_01"
                },
                {
                    "situation": "let_me_think",
                    "when_context_has": ["pain", "product_interest"],
                    "use": "kahneman_loss_aversion_01"
                }
            ],
            "fallback": {
                "default": "voss_mirroring_01",
                "when_no_context": "voss_mirroring_01",
                "after_failed_attempt_1": "voss_labeling_01",
                "after_failed_attempt_2": "cialdini_commitment_01"
            }
        }
    }


@pytest.fixture
def sample_principles():
    """Sample principles for testing."""
    return [
        {
            "principle_id": "kahneman_loss_aversion_01",
            "name": "Loss Aversion",
            "definition": "People feel losses more strongly than gains",
            "mechanism": "Loss framing increases motivation",
            "intervention": "Frame in terms of what they'll lose",
            "source": {"author": "Kahneman", "book": "Thinking Fast and Slow"}
        },
        {
            "principle_id": "voss_labeling_01",
            "name": "Labeling",
            "definition": "Label emotions to build rapport",
            "mechanism": "Acknowledgment builds trust",
            "intervention": "Name the emotion they're feeling",
            "source": {"author": "Voss", "book": "Never Split the Difference"}
        },
        {
            "principle_id": "cialdini_authority_01",
            "name": "Authority",
            "definition": "People defer to authority",
            "mechanism": "Authority signals expertise",
            "intervention": "Show credentials and expertise",
            "source": {"author": "Cialdini", "book": "Influence"}
        },
        {
            "principle_id": "kahneman_certainty_effect_01",
            "name": "Certainty Effect",
            "definition": "People prefer certain outcomes",
            "mechanism": "Certainty reduces anxiety",
            "intervention": "Offer guarantees and warranties",
            "source": {"author": "Kahneman", "book": "Thinking Fast and Slow"}
        },
        {
            "principle_id": "voss_mirroring_01",
            "name": "Mirroring",
            "definition": "Mirror body language and words",
            "mechanism": "Mirroring builds rapport",
            "intervention": "Repeat their last few words",
            "source": {"author": "Voss", "book": "Never Split the Difference"}
        },
        {
            "principle_id": "cialdini_commitment_01",
            "name": "Commitment",
            "definition": "People honor commitments",
            "mechanism": "Commitment creates consistency pressure",
            "intervention": "Get small commitment first",
            "source": {"author": "Cialdini", "book": "Influence"}
        }
    ]


@pytest.fixture
def selector(sample_selector_rules, sample_principles):
    """Create a PrincipleSelector instance for testing."""
    return PrincipleSelector(sample_selector_rules, sample_principles)


class TestPrincipleSelectorInitialization:
    """Test PrincipleSelector initialization."""
    
    def test_rules_loaded(self, sample_selector_rules, sample_principles):
        """Test rules are loaded correctly."""
        selector = PrincipleSelector(sample_selector_rules, sample_principles)
        assert len(selector.rules) == 5
    
    def test_fallback_loaded(self, sample_selector_rules, sample_principles):
        """Test fallback is loaded correctly."""
        selector = PrincipleSelector(sample_selector_rules, sample_principles)
        assert selector.fallback["default"] == "voss_mirroring_01"
        assert selector.fallback["after_failed_attempt_2"] == "cialdini_commitment_01"
    
    def test_principles_dict_created(self, sample_selector_rules, sample_principles):
        """Test principles dict is created correctly."""
        selector = PrincipleSelector(sample_selector_rules, sample_principles)
        assert "kahneman_loss_aversion_01" in selector.principles
        assert selector.principles["kahneman_loss_aversion_01"]["name"] == "Loss Aversion"
    
    def test_situation_mapping_created(self, sample_selector_rules, sample_principles):
        """Test situation mapping is created correctly."""
        selector = PrincipleSelector(sample_selector_rules, sample_principles)
        assert "price_objection" in selector.situation_mapping
        assert selector.situation_mapping["price_objection"] == "price_shock_in_store"


class TestSituationNormalization:
    """Test situation normalization."""
    
    def test_mapping_from_rule_name_to_situation_key(self, selector):
        """Test mapping from rule name to situation key."""
        # Rule name "price_objection" should map to "price_shock_in_store"
        normalized = selector._normalize_situation("price_objection")
        assert normalized == "price_shock_in_store"
    
    def test_already_normalized_situation(self, selector):
        """Test already normalized situation (no mapping needed)."""
        # Situation key already correct
        normalized = selector._normalize_situation("price_shock_in_store")
        assert normalized == "price_shock_in_store"
    
    def test_unknown_situation_returns_as_is(self, selector):
        """Test unknown situation returns as-is."""
        normalized = selector._normalize_situation("unknown_situation")
        assert normalized == "unknown_situation"


class TestRuleMatching:
    """Test rule matching logic."""
    
    def test_direct_situation_match(self, selector):
        """Test direct situation match (no context conditions)."""
        result = selector.select(
            situation="comparing_online",
            context={},
            principle_history=[],
            resistance_count=0
        )
        assert result["principle"]["principle_id"] == "cialdini_authority_01"
        assert "rule_match" in result["reason"]
    
    def test_context_conditions_match_when_context_has(self, selector):
        """Test context conditions match (when_context_has)."""
        result = selector.select(
            situation="price_objection",
            context={"pain": "back pain"},
            principle_history=[],
            resistance_count=0
        )
        assert result["principle"]["principle_id"] == "kahneman_loss_aversion_01"
        assert "rule_match" in result["reason"]
    
    def test_context_conditions_match_when_context_missing(self, selector):
        """Test context conditions match (when_context_missing)."""
        result = selector.select(
            situation="price_objection",
            context={},  # No pain
            principle_history=[],
            resistance_count=0
        )
        assert result["principle"]["principle_id"] == "voss_labeling_01"
        assert "rule_match" in result["reason"]
    
    def test_multiple_context_conditions_all_required(self, selector):
        """Test multiple context conditions all required (AND logic)."""
        result = selector.select(
            situation="let_me_think",
            context={"pain": "back pain", "product_interest": "chair"},
            principle_history=[],
            resistance_count=0
        )
        assert result["principle"]["principle_id"] == "kahneman_loss_aversion_01"
    
    def test_multiple_context_conditions_fails_when_missing(self, selector):
        """Test multiple context conditions fail when missing one."""
        # Missing product_interest
        result = selector.select(
            situation="let_me_think",
            context={"pain": "back pain"},  # Missing product_interest
            principle_history=[],
            resistance_count=0
        )
        # Should fall back to default (no match)
        assert result["principle"]["principle_id"] == "voss_mirroring_01"
        assert result["reason"] == "no_rule_match"
    
    def test_no_match_returns_fallback(self, selector):
        """Test no match returns fallback."""
        result = selector.select(
            situation="unknown_situation",
            context={},
            principle_history=[],
            resistance_count=0
        )
        assert result["principle"]["principle_id"] == "voss_mirroring_01"
        assert result["reason"] == "no_rule_match"


class TestContextConditionChecking:
    """Test context condition checking."""
    
    def test_when_context_has_all_required(self, selector):
        """Test when_context_has requires all specified keys."""
        rule = {
            "situation": "test",
            "when_context_has": ["pain", "product_interest"],
            "use": "test_principle"
        }
        
        # All present - should match
        context1 = {"pain": "value", "product_interest": "value"}
        assert selector._check_conditions(rule, context1) is True
        
        # Missing one - should not match
        context2 = {"pain": "value"}
        assert selector._check_conditions(rule, context2) is False
    
    def test_when_context_missing_excludes_forbidden(self, selector):
        """Test when_context_missing excludes forbidden keys."""
        rule = {
            "situation": "test",
            "when_context_missing": ["pain"],
            "use": "test_principle"
        }
        
        # Pain absent - should match
        context1 = {}
        assert selector._check_conditions(rule, context1) is True
        
        # Pain present - should not match
        context2 = {"pain": "value"}
        assert selector._check_conditions(rule, context2) is False
    
    def test_empty_conditions_always_match(self, selector):
        """Test empty conditions always match."""
        rule = {"situation": "test", "use": "test_principle"}
        context = {}
        assert selector._check_conditions(rule, context) is True
    
    def test_missing_context_keys(self, selector):
        """Test missing context keys."""
        rule = {
            "situation": "test",
            "when_context_has": ["pain"],
            "use": "test_principle"
        }
        context = {}
        assert selector._check_conditions(rule, context) is False


class TestFallbackLogic:
    """Test fallback logic."""
    
    def test_fallback_after_resistance_2(self, selector):
        """Test fallback after 2+ resistances."""
        result = selector.select(
            situation="price_objection",
            context={"pain": "back pain"},
            principle_history=[],
            resistance_count=2
        )
        assert result["principle"]["principle_id"] == "cialdini_commitment_01"
        assert result["reason"] == "fallback_after_resistance_2"
    
    def test_fallback_after_resistance_1(self, selector):
        """Test fallback after 1 resistance."""
        result = selector.select(
            situation="price_objection",
            context={"pain": "back pain"},
            principle_history=[],
            resistance_count=1
        )
        assert result["principle"]["principle_id"] == "voss_labeling_01"
        assert result["reason"] == "fallback_after_resistance_1"
    
    def test_fallback_when_no_context(self, selector):
        """Test fallback when no context."""
        result = selector.select(
            situation="price_objection",
            context={},
            principle_history=[],
            resistance_count=0
        )
        # Should try to match rule first (when_context_missing matches empty context)
        # But if no rule matches, should use fallback
        # In this case, price_objection with no pain should match "when_context_missing" rule
        assert result["principle"]["principle_id"] in ["voss_labeling_01", "voss_mirroring_01"]


class TestPrincipleRepetitionPrevention:
    """Test principle repetition prevention."""
    
    def test_principle_repetition_prevention(self, selector):
        """Test same principle not used 3+ times consecutively."""
        principle_history = [
            "kahneman_loss_aversion_01",
            "kahneman_loss_aversion_01"
        ]
        
        # Should not match because already used 2 times (last 3 window)
        # Note: The selector checks recent uses before selecting
        result = selector.select(
            situation="price_objection",
            context={"pain": "back pain"},
            principle_history=principle_history,
            resistance_count=0
        )
        # Should use fallback instead of repeating
        assert result["principle"]["principle_id"] == "voss_mirroring_01"
    
    def test_count_recent_uses(self, selector):
        """Test recent uses count calculation."""
        history = [
            "principle_1",
            "principle_2",
            "principle_1",
            "principle_1",
            "principle_3"
        ]
        
        # Last 3: ["principle_1", "principle_1", "principle_3"]
        count = selector._count_recent_uses("principle_1", history, window=3)
        assert count == 2
    
    def test_count_recent_uses_with_small_history(self, selector):
        """Test recent uses count with small history."""
        history = ["principle_1", "principle_1"]
        
        count = selector._count_recent_uses("principle_1", history, window=3)
        assert count == 2


class TestGetFallbackPrinciple:
    """Test get_fallback_principle method."""
    
    def test_fallback_after_resistance_2(self, selector):
        """Test fallback principle after 2+ resistances."""
        result = selector.get_fallback_principle(resistance_count=2)
        assert result["principle_id"] == "cialdini_commitment_01"
    
    def test_fallback_after_resistance_1(self, selector):
        """Test fallback principle after 1 resistance."""
        result = selector.get_fallback_principle(resistance_count=1)
        assert result["principle_id"] == "voss_labeling_01"
    
    def test_fallback_when_no_context(self, selector):
        """Test fallback principle when no context."""
        result = selector.get_fallback_principle(context=None)
        assert result["principle_id"] == "voss_mirroring_01"
    
    def test_default_fallback(self, selector):
        """Test default fallback principle."""
        result = selector.get_fallback_principle()
        assert result["principle_id"] == "voss_mirroring_01"

