"""
Unit tests for ResponseBuilder.

Tests response structure building, persona detection, qualification checklist, and next probe logic.
"""
import pytest
from sales_agent.engine.response_builder import ResponseBuilder


@pytest.fixture
def sample_principles():
    """Sample principles dict for testing."""
    return {
        "kahneman_loss_aversion_01": {
            "principle_id": "kahneman_loss_aversion_01",
            "name": "Loss Aversion",
            "definition": "People feel losses more strongly than gains",
            "mechanism": "Loss framing increases motivation",
            "intervention": "Frame in terms of what they'll lose",
            "source": {
                "author": "Kahneman",
                "book": "Thinking Fast and Slow",
                "chapter": 26,
                "page": 284
            }
        },
        "cialdini_commitment_01": {
            "principle_id": "cialdini_commitment_01",
            "name": "Commitment",
            "definition": "People honor commitments",
            "mechanism": "Commitment creates consistency pressure",
            "intervention": "Get small commitment first",
            "source": {
                "author": "Robert Cialdini",
                "book": "Influence",
                "chapter": 3,
                "page": 57
            }
        },
        "voss_mirroring_01": {
            "principle_id": "voss_mirroring_01",
            "name": "Mirroring",
            "definition": "Mirror body language and words",
            "mechanism": "Mirroring builds rapport",
            "intervention": "Repeat their last few words",
            "source": "Chris Voss, Never Split the Difference"
        }
    }


@pytest.fixture
def sample_capture_schema():
    """Sample capture schema for testing."""
    return {
        "capture_schema": {
            "slots": {
                "pain": {
                    "description": "Customer's pain point",
                    "priority": "high"
                },
                "product_interest": {
                    "description": "Product customer is interested in",
                    "priority": "high"
                }
            }
        }
    }


@pytest.fixture
def response_builder(sample_principles, sample_capture_schema):
    """Create a ResponseBuilder instance for testing."""
    return ResponseBuilder(sample_principles, sample_capture_schema)


class TestResponseBuilderInitialization:
    """Test ResponseBuilder initialization."""
    
    def test_principles_loaded(self, sample_principles, sample_capture_schema):
        """Test principles are loaded correctly."""
        builder = ResponseBuilder(sample_principles, sample_capture_schema)
        assert builder.principles == sample_principles
    
    def test_capture_schema_loaded(self, sample_principles, sample_capture_schema):
        """Test capture schema is loaded correctly."""
        builder = ResponseBuilder(sample_principles, sample_capture_schema)
        assert builder.capture_schema == sample_capture_schema
    
    def test_slots_extracted(self, sample_principles, sample_capture_schema):
        """Test slots are extracted correctly."""
        builder = ResponseBuilder(sample_principles, sample_capture_schema)
        assert "pain" in builder.slots
        assert "product_interest" in builder.slots


class TestResponseStructure:
    """Test response structure building."""
    
    def test_response_structure_complete(self, response_builder, sample_principles):
        """Test response has all required fields."""
        result = response_builder.build(
            customer_message="This is too expensive",
            customer_facing_response="I understand price is important to you.",
            detection_result={
                "situation": "price_shock_in_store",
                "confidence": 0.9,
                "stage": "objection_handling"
            },
            captured_context={"pain": "back pain"},
            captured_quotes=["too expensive"],
            recommendation={
                "principle": sample_principles["kahneman_loss_aversion_01"],
                "reason": "rule_match"
            },
            fallback_principle=sample_principles["voss_mirroring_01"],
            session_id="test-session",
            turn_count=1,
            resistance_count=0,
            principles_used=["kahneman_loss_aversion_01"],
            latency_ms=150
        )
        
        # Test top-level structure
        assert "customer_facing" in result
        assert "agent_dashboard" in result
        
        # Test customer_facing
        assert "response" in result["customer_facing"]
        assert result["customer_facing"]["response"] == "I understand price is important to you."
        
        # Test agent_dashboard structure
        dashboard = result["agent_dashboard"]
        required_fields = [
            "detection", "captured_context", "captured_quotes",
            "qualification_checklist", "recommendation", "fallback",
            "next_probe", "session", "system"
        ]
        for field in required_fields:
            assert field in dashboard, f"Missing field: {field}"
    
    def test_detection_structure(self, response_builder, sample_principles):
        """Test detection structure is correct."""
        result = response_builder.build(
            customer_message="This is too expensive",
            customer_facing_response="I understand.",
            detection_result={
                "situation": "price_shock_in_store",
                "confidence": 0.9,
                "stage": "objection_handling"
            },
            captured_context={},
            captured_quotes=[],
            recommendation={"principle": sample_principles["kahneman_loss_aversion_01"]},
            fallback_principle=sample_principles["voss_mirroring_01"],
            session_id="test",
            turn_count=1,
            resistance_count=0,
            principles_used=[],
            latency_ms=100
        )
        
        detection = result["agent_dashboard"]["detection"]
        assert detection["customer_said"] == "This is too expensive"
        assert detection["detected_situation"] == "price_shock_in_store"
        assert detection["situation_confidence"] == 0.9
        assert detection["micro_stage"] == "objection_handling"
        assert "detected_persona" in detection
        assert "persona_confidence" in detection
    
    def test_session_structure(self, response_builder, sample_principles):
        """Test session structure is correct."""
        result = response_builder.build(
            customer_message="Test message",
            customer_facing_response="Test response",
            detection_result={"situation": "test", "confidence": 0.8, "stage": "discovery"},
            captured_context={},
            captured_quotes=[],
            recommendation={"principle": sample_principles["kahneman_loss_aversion_01"]},
            fallback_principle=sample_principles["voss_mirroring_01"],
            session_id="test-session-123",
            turn_count=3,
            resistance_count=2,
            principles_used=["principle_1", "principle_2"],
            latency_ms=200
        )
        
        session = result["agent_dashboard"]["session"]
        assert session["session_id"] == "test-session-123"
        assert session["turn_count"] == 3
        assert session["resistance_count"] == 2
        assert session["principles_used"] == ["principle_1", "principle_2"]
    
    def test_system_structure(self, response_builder, sample_principles):
        """Test system structure is correct."""
        result = response_builder.build(
            customer_message="Test message",
            customer_facing_response="Test response",
            detection_result={"situation": "test", "confidence": 0.8, "stage": "discovery"},
            captured_context={},
            captured_quotes=[],
            recommendation={"principle": sample_principles["kahneman_loss_aversion_01"]},
            fallback_principle=sample_principles["voss_mirroring_01"],
            session_id="test",
            turn_count=1,
            resistance_count=0,
            principles_used=[],
            latency_ms=175,
            step_latencies={"capture": 50, "detect": 60, "generate": 65}
        )
        
        system = result["agent_dashboard"]["system"]
        assert system["latency_ms"] == 175
        assert system["step_latencies"] == {"capture": 50, "detect": 60, "generate": 65}


class TestPersonaDetection:
    """Test persona detection logic."""
    
    def test_price_conscious_persona(self, response_builder):
        """Test price_conscious persona detection."""
        persona = response_builder._detect_persona(
            customer_message="This is too expensive for my budget",
            situation="price_shock_in_store",
            context={"budget_signal": "high"}
        )
        assert persona["persona"] == "price_conscious"
        assert persona["confidence"] > 0.5
    
    def test_price_conscious_with_situation_match(self, response_builder):
        """Test price_conscious persona with situation match (higher confidence)."""
        persona = response_builder._detect_persona(
            customer_message="Too expensive",
            situation="price_shock_in_store",
            context={}
        )
        assert persona["persona"] == "price_conscious"
        # Signal + situation match should give higher confidence
        assert persona["confidence"] >= 0.70
    
    def test_research_oriented_persona(self, response_builder):
        """Test research_oriented persona detection."""
        persona = response_builder._detect_persona(
            customer_message="I need to research this more before deciding",
            situation="want_to_research_more",
            context={}
        )
        assert persona["persona"] == "research_oriented"
        assert persona["confidence"] > 0.5
    
    def test_risk_averse_persona(self, response_builder):
        """Test risk_averse persona detection."""
        persona = response_builder._detect_persona(
            customer_message="What if it breaks? What's the warranty?",
            situation="warranty_and_service_concern",
            context={}
        )
        assert persona["persona"] == "risk_averse"
        assert persona["confidence"] > 0.5
    
    def test_ready_to_buy_persona(self, response_builder):
        """Test ready_to_buy persona detection."""
        persona = response_builder._detect_persona(
            customer_message="I'm ready to buy this today",
            situation="second_visit_return",
            context={}
        )
        assert persona["persona"] == "ready_to_buy"
        assert persona["confidence"] > 0.5
    
    def test_exploratory_persona_default(self, response_builder):
        """Test exploratory persona as default."""
        persona = response_builder._detect_persona(
            customer_message="Just looking around",
            situation="just_browsing",
            context={}
        )
        assert persona["persona"] == "exploratory"
        assert persona["confidence"] == 0.60


class TestQualificationChecklist:
    """Test qualification checklist building."""
    
    def test_need_identified(self, response_builder):
        """Test need_identified checklist item."""
        checklist = response_builder._build_qualification_checklist({
            "pain": "back pain"
        })
        assert checklist["need_identified"] is True
        
        checklist2 = response_builder._build_qualification_checklist({
            "trigger_event": "moving"
        })
        assert checklist2["need_identified"] is True
    
    def test_pain_expressed(self, response_builder):
        """Test pain_expressed checklist item."""
        checklist = response_builder._build_qualification_checklist({
            "pain": "back pain"
        })
        assert checklist["pain_expressed"] is True
        
        checklist2 = response_builder._build_qualification_checklist({})
        assert checklist2["pain_expressed"] is False
    
    def test_product_interest(self, response_builder):
        """Test product_interest checklist item."""
        checklist = response_builder._build_qualification_checklist({
            "product_interest": "office chair"
        })
        assert checklist["product_interest"] is True
    
    def test_budget_discussed(self, response_builder):
        """Test budget_discussed checklist item."""
        checklist = response_builder._build_qualification_checklist({
            "budget_signal": "high"
        })
        assert checklist["budget_discussed"] is True
        
        checklist2 = response_builder._build_qualification_checklist({
            "payment_preference": "credit card"
        })
        assert checklist2["budget_discussed"] is True
    
    def test_timeline_known(self, response_builder):
        """Test timeline_known checklist item."""
        checklist = response_builder._build_qualification_checklist({
            "timeline": "urgent"
        })
        assert checklist["timeline_known"] is True
    
    def test_decision_maker_known(self, response_builder):
        """Test decision_maker_known checklist item."""
        checklist = response_builder._build_qualification_checklist({
            "decision_maker": "self"
        })
        assert checklist["decision_maker_known"] is True
        
        # If need_to_check_with_family is present and truthy, decision_maker is unknown
        checklist2 = response_builder._build_qualification_checklist({
            "need_to_check_with_family": True
        })
        assert checklist2["decision_maker_known"] is False
    
    def test_all_false_when_empty_context(self, response_builder):
        """Test all checklist items false when context is empty."""
        checklist = response_builder._build_qualification_checklist({})
        assert checklist["need_identified"] is False
        assert checklist["pain_expressed"] is False
        assert checklist["product_interest"] is False
        assert checklist["budget_discussed"] is False
        assert checklist["timeline_known"] is False


class TestNextProbe:
    """Test next probe determination."""
    
    def test_probe_pain_first_priority(self, response_builder):
        """Test pain is probed first (highest priority)."""
        probe = response_builder._determine_next_probe(
            context={},
            qualification_checklist={
                "pain_expressed": False,
                "timeline_known": False,
                "budget_discussed": False
            }
        )
        assert probe["target"] == "pain"
        assert "problem" in probe["question"].lower()
    
    def test_probe_timeline_second_priority(self, response_builder):
        """Test timeline is probed second (when pain known)."""
        probe = response_builder._determine_next_probe(
            context={"pain": "back pain"},
            qualification_checklist={
                "pain_expressed": True,
                "timeline_known": False,
                "budget_discussed": False
            }
        )
        assert probe["target"] == "timeline"
        assert "when" in probe["question"].lower()
    
    def test_probe_budget_third_priority(self, response_builder):
        """Test budget is probed third (when pain and timeline known)."""
        probe = response_builder._determine_next_probe(
            context={"pain": "back pain", "timeline": "urgent"},
            qualification_checklist={
                "pain_expressed": True,
                "timeline_known": True,
                "budget_discussed": False
            }
        )
        assert probe["target"] == "budget"
        assert "budget" in probe["question"].lower()
    
    def test_probe_deeper_context_when_all_filled(self, response_builder):
        """Test probes deeper context when all high-priority items filled."""
        probe = response_builder._determine_next_probe(
            context={
                "pain": "back pain",
                "timeline": "urgent",
                "budget_signal": "high",
                "decision_maker": "self",
                "product_interest": "chair"
            },
            qualification_checklist={
                "pain_expressed": True,
                "timeline_known": True,
                "budget_discussed": True,
                "decision_maker_known": True,
                "product_interest": True
            }
        )
        # Should probe for duration or current_state
        assert probe["target"] in ["duration", "current_state", "commitment"]


class TestRecommendationFormatting:
    """Test recommendation formatting."""
    
    def test_recommendation_formatting_with_source(self, response_builder, sample_principles):
        """Test recommendation formatting with full source details."""
        recommendation = response_builder._format_recommendation({
            "principle": sample_principles["kahneman_loss_aversion_01"],
            "reason": "rule_match"
        })
        
        assert recommendation["principle"] == "Loss Aversion"
        assert recommendation["principle_id"] == "kahneman_loss_aversion_01"
        assert "Kahneman" in recommendation["source"]
        assert "Thinking Fast and Slow" in recommendation["source"]
        assert recommendation["approach"] == "Frame in terms of what they'll lose"
        assert recommendation["why_it_works"] == "Loss framing increases motivation"
    
    def test_recommendation_with_string_source(self, response_builder, sample_principles):
        """Test recommendation formatting with string source."""
        recommendation = response_builder._format_recommendation({
            "principle": sample_principles["voss_mirroring_01"],
            "reason": "rule_match"
        })
        
        assert recommendation["source"] == "Chris Voss, Never Split the Difference"


class TestFallbackFormatting:
    """Test fallback formatting."""
    
    def test_fallback_with_quotes(self, response_builder, sample_principles):
        """Test fallback formatting with captured quotes."""
        fallback = response_builder._format_fallback(
            fallback_principle=sample_principles["voss_mirroring_01"],
            captured_quotes=["too expensive", "not sure"]
        )
        
        assert fallback["principle"] == "Mirroring"
        assert fallback["principle_id"] == "voss_mirroring_01"
        assert "too expensive" in fallback["response"]  # Should use last quote
    
    def test_fallback_without_quotes(self, response_builder, sample_principles):
        """Test fallback formatting without quotes (default response)."""
        fallback = response_builder._format_fallback(
            fallback_principle=sample_principles["voss_mirroring_01"],
            captured_quotes=[]
        )
        
        assert fallback["principle"] == "Mirroring"
        assert "help you find" in fallback["response"].lower() or "brings you" in fallback["response"].lower()

