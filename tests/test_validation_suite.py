"""
Comprehensive Validation Test Suite
Covers all 10 validation tests from the MVP validation document
"""
import pytest
import asyncio
from typing import Dict, Any, List
import json
import time

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_PRODUCT_CONTEXT = {"name": "ErgoChair", "price": 899}


class ValidationTracker:
    """Tracks validation results across all tests."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
    
    def record_test(
        self, 
        test_name: str, 
        passed: bool, 
        details: Dict[str, Any] = None,
        errors: List[str] = None
    ):
        """Record a test result."""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
        
        result = {
            "test_name": test_name,
            "passed": passed,
            "timestamp": time.time(),
            "details": details or {},
            "errors": errors or []
        }
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "success_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0,
            "results": self.results
        }
    
    def export_json(self, filepath: str):
        """Export results to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.get_summary(), f, indent=2)


# Global tracker instance
tracker = ValidationTracker()


async def make_request(method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
    """Make HTTP request to API."""
    import aiohttp
    
    url = f"{BASE_URL}{endpoint}"
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url) as resp:
                if resp.status == 404:
                    raise Exception(f"404 Not Found: {endpoint}")
                resp.raise_for_status()
                return await resp.json()
        elif method == "POST":
            async with session.post(url, json=data) as resp:
                resp.raise_for_status()
                return await resp.json()
        elif method == "DELETE":
            async with session.delete(url) as resp:
                resp.raise_for_status()
                return await resp.json()


class TestValidationSuite:
    """All 10 validation tests."""
    
    @pytest.mark.asyncio
    async def test_1_health_check(self):
        """Test 1: Health Check"""
        test_name = "Test 1: Health Check"
        errors = []
        details = {}
        
        try:
            response = await make_request("GET", "/health")
            details["response"] = response
            
            # Validate response structure
            assert "status" in response, "Missing 'status' field"
            assert "llm_connection" in response, "Missing 'llm_connection' field"
            assert "config_loaded" in response, "Missing 'config_loaded' field"
            
            # Validate values
            if response["status"] != "ok":
                errors.append(f"Status is '{response['status']}', expected 'ok'")
            if response["llm_connection"] != "ok":
                errors.append(f"LLM connection is '{response['llm_connection']}', expected 'ok'")
            if response["config_loaded"] != True:
                errors.append(f"Config loaded is {response['config_loaded']}, expected True")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Health check failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_2_price_objection_with_pain(self):
        """Test 2: Price Objection (with pain)"""
        test_name = "Test 2: Price Objection (with pain)"
        errors = []
        details = {}
        
        try:
            session_id = "test-001"
            request_data = {
                "session_id": session_id,
                "message": "This looks good but 899 is too much. My back has been killing me for 3 years.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            
            response = await make_request("POST", "/chat", request_data)
            details["response"] = response
            
            dashboard = response.get("agent_dashboard", {})
            detection = dashboard.get("detection", {})
            captured = dashboard.get("captured_context", {})
            recommendation = dashboard.get("recommendation", {})
            customer_response = response.get("customer_facing", {}).get("response", "")
            
            # Validate detected situation
            if detection.get("detected_situation") != "price_objection":
                errors.append(f"Expected 'price_objection', got '{detection.get('detected_situation')}'")
            
            # Validate captured context
            if "pain" not in captured or not captured.get("pain"):
                errors.append("captured_context.pain is missing or empty")
            
            if "duration" not in captured or not captured.get("duration"):
                errors.append("captured_context.duration is missing or empty")
            
            # Validate principle selection
            principle_id = recommendation.get("principle_id", "")
            if "kahneman_loss_aversion" not in principle_id:
                errors.append(f"Expected principle with 'kahneman_loss_aversion', got '{principle_id}'")
            
            # Validate response uses customer's words
            if "back" not in customer_response.lower() or "3 years" not in customer_response.lower():
                errors.append("Response doesn't use customer's exact words ('back', '3 years')")
            
            # Validate response length (max 2 sentences)
            sentences = customer_response.split('.')
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) > 2:
                errors.append(f"Response has {len(sentences)} sentences, max is 2")
            
            # Validate fallback exists
            fallback = dashboard.get("fallback", {})
            if not fallback or not fallback.get("principle_id"):
                errors.append("Fallback is missing or incomplete")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 2 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_3_price_objection_no_pain(self):
        """Test 3: Price Objection (no pain)"""
        test_name = "Test 3: Price Objection (no pain)"
        errors = []
        details = {}
        
        try:
            session_id = "test-002"
            request_data = {
                "session_id": session_id,
                "message": "That's too expensive.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            
            response = await make_request("POST", "/chat", request_data)
            details["response"] = response
            
            dashboard = response.get("agent_dashboard", {})
            detection = dashboard.get("detection", {})
            captured = dashboard.get("captured_context", {})
            recommendation = dashboard.get("recommendation", {})
            
            # Validate detected situation
            if detection.get("detected_situation") != "price_objection":
                errors.append(f"Expected 'price_objection', got '{detection.get('detected_situation')}'")
            
            # Validate pain is NOT captured
            if captured.get("pain"):
                errors.append("captured_context.pain should be null/missing, but it exists")
            
            # Validate principle selection (should be voss_labeling, not loss_aversion)
            principle_id = recommendation.get("principle_id", "")
            if "voss_labeling" not in principle_id:
                errors.append(f"Expected 'voss_labeling' principle (no pain), got '{principle_id}'")
            
            if "kahneman_loss_aversion" in principle_id:
                errors.append("Should NOT use loss_aversion when no pain is expressed")
            
            # Validate response tries to uncover pain
            customer_response = response.get("customer_facing", {}).get("response", "")
            pain_keywords = ["why", "what", "tell me", "help me understand"]
            if not any(keyword in customer_response.lower() for keyword in pain_keywords):
                errors.append("Response should try to uncover pain (ask questions)")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 3 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_4_warranty_concern(self):
        """Test 4: Warranty Concern"""
        test_name = "Test 4: Warranty Concern"
        errors = []
        details = {}
        
        try:
            session_id = "test-003"
            request_data = {
                "session_id": session_id,
                "message": "What if it breaks after 6 months? Who fixes it?",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            
            response = await make_request("POST", "/chat", request_data)
            details["response"] = response
            
            dashboard = response.get("agent_dashboard", {})
            detection = dashboard.get("detection", {})
            captured = dashboard.get("captured_context", {})
            recommendation = dashboard.get("recommendation", {})
            
            # Validate detected situation
            if "warranty" not in detection.get("detected_situation", "").lower():
                errors.append(f"Expected warranty-related situation, got '{detection.get('detected_situation')}'")
            
            # Validate captured context
            if "warranty_service_concern" not in captured or not captured.get("warranty_service_concern"):
                errors.append("captured_context.warranty_service_concern is missing or empty")
            
            # Validate principle selection
            principle_id = recommendation.get("principle_id", "")
            if "kahneman_certainty_effect" not in principle_id:
                errors.append(f"Expected 'kahneman_certainty_effect' principle, got '{principle_id}'")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 4 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_5_comparing_online(self):
        """Test 5: Comparing Online"""
        test_name = "Test 5: Comparing Online"
        errors = []
        details = {}
        
        try:
            session_id = "test-004"
            request_data = {
                "session_id": session_id,
                "message": "I saw this same chair on Amazon for 750.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            
            response = await make_request("POST", "/chat", request_data)
            details["response"] = response
            
            dashboard = response.get("agent_dashboard", {})
            detection = dashboard.get("detection", {})
            captured = dashboard.get("captured_context", {})
            recommendation = dashboard.get("recommendation", {})
            
            # Validate detected situation
            if "comparing" not in detection.get("detected_situation", "").lower() and \
               "online" not in detection.get("detected_situation", "").lower():
                errors.append(f"Expected comparing_online situation, got '{detection.get('detected_situation')}'")
            
            # Validate captured context
            if "competitor_mention" not in captured or not captured.get("competitor_mention"):
                errors.append("captured_context.competitor_mention is missing or empty")
            
            # Validate principle selection
            principle_id = recommendation.get("principle_id", "")
            if "cialdini_authority" not in principle_id:
                errors.append(f"Expected 'cialdini_authority' principle, got '{principle_id}'")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 5 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_6_multi_turn_conversation(self):
        """Test 6: Multi-Turn Conversation"""
        test_name = "Test 6: Multi-Turn Conversation"
        errors = []
        details = {}
        
        try:
            session_id = "test-005"
            
            # Turn 1
            turn1_data = {
                "session_id": session_id,
                "message": "I'm looking for a good office chair.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            response1 = await make_request("POST", "/chat", turn1_data)
            details["turn1"] = response1
            
            # Turn 2
            turn2_data = {
                "session_id": session_id,
                "message": "899 seems steep though. I've had back pain for years.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            response2 = await make_request("POST", "/chat", turn2_data)
            details["turn2"] = response2
            
            # Get session state
            session_response = await make_request("GET", f"/session/{session_id}")
            details["session_state"] = session_response
            
            # Validate session state persists
            if not session_response:
                errors.append("Session state not found")
            else:
                # Validate accumulated context
                captured_context = session_response.get("captured_context", {})
                if not captured_context:
                    errors.append("captured_context is empty - should accumulate across turns")
                
                # Validate captured_quotes grows
                quotes = session_response.get("captured_quotes", [])
                if len(quotes) < 2:
                    errors.append(f"captured_quotes should have multiple quotes, got {len(quotes)}")
                
                # Validate turn_count increments
                turn_count = response2.get("agent_dashboard", {}).get("session", {}).get("turn_count", 0)
                if turn_count != 2:
                    errors.append(f"turn_count should be 2, got {turn_count}")
                
                # Validate principle_history tracks both
                principle_history = session_response.get("principle_history", [])
                if len(principle_history) < 2:
                    errors.append(f"principle_history should have 2 entries, got {len(principle_history)}")
                
                # Validate context accumulates (not reset)
                dashboard2 = response2.get("agent_dashboard", {})
                context2 = dashboard2.get("captured_context", {})
                if len(context2) < len(captured_context):
                    errors.append("Context in turn 2 should accumulate from turn 1")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 6 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_7_session_state(self):
        """Test 7: Session State"""
        test_name = "Test 7: Session State"
        errors = []
        details = {}
        
        try:
            session_id = "test-007"
            
            # Create a session with a message
            request_data = {
                "session_id": session_id,
                "message": "This chair is too expensive.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            await make_request("POST", "/chat", request_data)
            
            # Get session state
            session_response = await make_request("GET", f"/session/{session_id}")
            details["session_response"] = session_response
            
            # Validate all required fields exist
            required_fields = [
                "captured_context",
                "captured_quotes",
                "conversation_history",
                "principle_history",
            ]
            
            for field in required_fields:
                if field not in session_response:
                    errors.append(f"Missing required field: {field}")
            
            # Validate conversation_history structure
            conv_history = session_response.get("conversation_history", [])
            if len(conv_history) > 0:
                first_turn = conv_history[0]
                if "customer" not in first_turn or "agent" not in first_turn:
                    errors.append("conversation_history entries should have 'customer' and 'agent' fields")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 7 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_8_session_clear(self):
        """Test 8: Session Clear"""
        test_name = "Test 8: Session Clear"
        errors = []
        details = {}
        
        try:
            session_id = "test-008"
            
            # Create a session
            request_data = {
                "session_id": session_id,
                "message": "Test message",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            await make_request("POST", "/chat", request_data)
            
            # Verify session exists
            session_before = await make_request("GET", f"/session/{session_id}")
            if not session_before:
                errors.append("Session should exist before delete")
            
            # Delete session
            delete_response = await make_request("DELETE", f"/session/{session_id}")
            details["delete_response"] = delete_response
            
            # Validate DELETE response
            if delete_response.get("status") != "cleared":
                errors.append(f"DELETE should return {{'status': 'cleared'}}, got {delete_response}")
            
            # Verify session is gone
            try:
                session_after = await make_request("GET", f"/session/{session_id}")
                # Should not reach here - should get 404
                errors.append("Session should return 404 after delete")
            except Exception as e:
                # Expected - session should be deleted
                if "404" not in str(e) and "not found" not in str(e).lower():
                    errors.append(f"Expected 404, got: {str(e)}")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 8 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_9_resistance_fallback(self):
        """Test 9: Resistance Fallback"""
        test_name = "Test 9: Resistance Fallback"
        errors = []
        details = {}
        
        try:
            session_id = "test-006"
            
            # Turn 1: First resistance
            turn1 = {
                "session_id": session_id,
                "message": "Too expensive.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            response1 = await make_request("POST", "/chat", turn1)
            details["turn1"] = response1
            
            # Turn 2: Second resistance
            turn2 = {
                "session_id": session_id,
                "message": "Still no, not worth it.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            response2 = await make_request("POST", "/chat", turn2)
            details["turn2"] = response2
            
            # Turn 3: Third resistance - should trigger fallback
            turn3 = {
                "session_id": session_id,
                "message": "I said no.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            response3 = await make_request("POST", "/chat", turn3)
            details["turn3"] = response3
            
            # Validate resistance_count increments
            session_state = await make_request("GET", f"/session/{session_id}")
            resistance_count = response3.get("agent_dashboard", {}).get("session", {}).get("resistance_count", 0)
            
            if resistance_count < 3:
                errors.append(f"resistance_count should be >= 3, got {resistance_count}")
            
            # Validate fallback principle is used after turn 3
            principle_id_turn3 = response3.get("agent_dashboard", {}).get("recommendation", {}).get("principle_id", "")
            
            # After 2+ resistance, should use commitment/fallback principle
            if "cialdini_commitment" not in principle_id_turn3.lower() and \
               "fallback" not in principle_id_turn3.lower():
                # Check if it's at least a softer principle
                if "kahneman_loss_aversion" in principle_id_turn3:
                    errors.append("Should use fallback/commitment principle after 3 resistances, not loss_aversion")
            
            # Validate response offers reduced commitment
            response_text = response3.get("customer_facing", {}).get("response", "").lower()
            reduced_commitment_keywords = ["trial", "sample", "try", "test", "risk-free", "guarantee"]
            if not any(keyword in response_text for keyword in reduced_commitment_keywords):
                errors.append("Response should offer reduced commitment (trial, sample, etc.) after resistance")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 9 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_10_no_principle_repetition(self):
        """Test 10: No Principle Repetition"""
        test_name = "Test 10: No Principle Repetition"
        errors = []
        details = {}
        
        try:
            session_id = "test-010"
            principle_ids = []
            
            # Send 4 messages with same situation (price_objection with pain)
            messages = [
                "This is too expensive, my back hurts.",
                "Still too much, my back has been hurting for years.",
                "The price is still too high for my bad back.",
                "I can't afford this, my back pain is killing me."
            ]
            
            for i, message in enumerate(messages):
                request_data = {
                    "session_id": session_id,
                    "message": message,
                    "product_context": TEST_PRODUCT_CONTEXT
                }
                response = await make_request("POST", "/chat", request_data)
                principle_id = response.get("agent_dashboard", {}).get("recommendation", {}).get("principle_id", "")
                principle_ids.append(principle_id)
                details[f"turn{i+1}"] = {"principle_id": principle_id}
            
            # Validate principle variation
            details["all_principles"] = principle_ids
            
            # Check if same principle used 3+ times consecutively
            consecutive_count = 1
            max_consecutive = 1
            for i in range(1, len(principle_ids)):
                if principle_ids[i] == principle_ids[i-1]:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    consecutive_count = 1
            
            if max_consecutive > 2:
                errors.append(f"Same principle used {max_consecutive} times consecutively (max allowed is 2)")
            
            # Validate principle_history shows variation
            session_state = await make_request("GET", f"/session/{session_id}")
            principle_history = session_state.get("principle_history", [])
            
            if len(set(principle_history)) < 2:
                errors.append(f"principle_history should show variation, got {len(set(principle_history))} unique principles")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Test 10 failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise
    
    @pytest.mark.asyncio
    async def test_response_structure_validation(self):
        """Additional: Validate response structure matches schema"""
        test_name = "Response Structure Validation"
        errors = []
        details = {}
        
        try:
            session_id = "test-structure"
            request_data = {
                "session_id": session_id,
                "message": "This is too expensive.",
                "product_context": TEST_PRODUCT_CONTEXT
            }
            
            response = await make_request("POST", "/chat", request_data)
            details["response"] = response
            
            # Validate top-level structure
            if "customer_facing" not in response:
                errors.append("Missing 'customer_facing' in response")
            if "agent_dashboard" not in response:
                errors.append("Missing 'agent_dashboard' in response")
            
            # Validate customer_facing
            customer_facing = response.get("customer_facing", {})
            if "response" not in customer_facing:
                errors.append("Missing 'customer_facing.response'")
            
            # Validate agent_dashboard structure
            dashboard = response.get("agent_dashboard", {})
            required_dashboard_fields = [
                "detection",
                "captured_context",
                "captured_quotes",
                "qualification_checklist",
                "recommendation",
                "fallback",
                "next_probe",
                "session",
                "system"
            ]
            
            for field in required_dashboard_fields:
                if field not in dashboard:
                    errors.append(f"Missing 'agent_dashboard.{field}'")
            
            # Validate detection structure
            detection = dashboard.get("detection", {})
            detection_fields = [
                "customer_said",
                "detected_situation",
                "situation_confidence",
                "micro_stage"
            ]
            for field in detection_fields:
                if field not in detection:
                    errors.append(f"Missing 'agent_dashboard.detection.{field}'")
            
            # Validate recommendation structure
            recommendation = dashboard.get("recommendation", {})
            rec_fields = [
                "principle",
                "principle_id",
                "source",
                "approach",
                "response",
                "why_it_works"
            ]
            for field in rec_fields:
                if field not in recommendation:
                    errors.append(f"Missing 'agent_dashboard.recommendation.{field}'")
            
            # Validate session structure
            session_info = dashboard.get("session", {})
            session_fields = ["session_id", "turn_count", "resistance_count", "principles_used"]
            for field in session_fields:
                if field not in session_info:
                    errors.append(f"Missing 'agent_dashboard.session.{field}'")
            
            # Validate system structure
            system_info = dashboard.get("system", {})
            if "latency_ms" not in system_info:
                errors.append("Missing 'agent_dashboard.system.latency_ms'")
            
            # Validate latency < 500ms
            latency = system_info.get("latency_ms", 0)
            if latency > 500:
                errors.append(f"Latency is {latency}ms, should be < 500ms")
            
            passed = len(errors) == 0
            tracker.record_test(test_name, passed, details, errors)
            assert passed, f"Response structure validation failed: {errors}"
            
        except Exception as e:
            tracker.record_test(test_name, False, details, [str(e)])
            raise

