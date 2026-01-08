"""
Unit tests for SalesAgentOrchestrator.

Tests full orchestration flow, cache integration, reconcile logic, and session state management.
"""
import pytest
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from sales_agent.engine.orchestrator import SalesAgentOrchestrator


@pytest.fixture
def sample_configs():
    """Sample configs for testing."""
    return {
        "principles.json": [
            {
                "principle_id": "kahneman_loss_aversion_01",
                "name": "Loss Aversion",
                "definition": "People feel losses more strongly",
                "mechanism": "Loss framing",
                "intervention": "Frame in terms of loss",
                "source": {"author": "Kahneman", "book": "Thinking Fast and Slow"}
            }
        ],
        "situations.json": {
            "price_shock_in_store": {
                "signals": ["expensive", "too much"],
                "stage": "objection_handling"
            },
            "just_browsing": {
                "signals": ["just looking"],
                "stage": "discovery"
            }
        },
        "principle_selector.json": {
            "principle_selector": {
                "rules": [
                    {
                        "situation": "price_objection",
                        "when_context_has": ["pain"],
                        "use": "kahneman_loss_aversion_01"
                    }
                ],
                "fallback": {
                    "default": "kahneman_loss_aversion_01",
                    "when_no_context": "kahneman_loss_aversion_01",
                    "after_failed_attempt_1": "kahneman_loss_aversion_01",
                    "after_failed_attempt_2": "kahneman_loss_aversion_01"
                }
            }
        },
        "capture_schema.json": {
            "capture_schema": {
                "slots": {
                    "pain": {"description": "Pain point", "priority": "high"},
                    "budget_signal": {"description": "Budget", "priority": "medium"}
                }
            }
        }
    }


@pytest.fixture
def mock_engines(sample_configs):
    """Mock all engines."""
    engines = {}
    
    # Mock CaptureEngine
    engines["capture"] = AsyncMock()
    engines["capture"].extract = AsyncMock(return_value={
        "slots": {"pain": "back pain"},
        "new_quotes": ["too expensive"]
    })
    
    # Mock SituationDetector
    engines["detector"] = AsyncMock()
    engines["detector"].detect = AsyncMock(return_value={
        "situation": "price_shock_in_store",
        "confidence": 0.9,
        "stage": "objection_handling"
    })
    
    # Mock ResponseGenerator
    engines["generator"] = AsyncMock()
    engines["generator"].generate = AsyncMock(return_value={
        "response": "I understand price is important to you.",
        "principle_used": "Loss Aversion"
    })
    
    return engines


@pytest.fixture
def mock_caches():
    """Mock caches."""
    caches = {}
    
    # Mock ExactCache
    caches["exact"] = MagicMock()
    caches["exact"].get = MagicMock(return_value=None)
    caches["exact"].set = MagicMock()
    caches["exact"].get_stats = MagicMock(return_value={"hits": 0, "misses": 0})
    
    # Mock SemanticCache
    caches["semantic"] = AsyncMock()
    caches["semantic"].get = AsyncMock(return_value=None)
    caches["semantic"].set = AsyncMock()
    caches["semantic"].get_stats = MagicMock(return_value={"hits": 0, "misses": 0})
    
    return caches


@pytest.fixture
def mock_llm_pool():
    """Mock LLM pool."""
    pool = MagicMock()
    pool.get_anthropic_client = MagicMock(return_value=MagicMock())
    pool.close = AsyncMock()
    pool.warmup = AsyncMock()
    return pool


@pytest.fixture
def mock_llm_router():
    """Mock LLM router."""
    router = MagicMock()
    router.call = AsyncMock(return_value=("response", "anthropic"))
    router.get_stats = MagicMock(return_value={"anthropic": {"wins": 0}})
    return router


@pytest.mark.asyncio
class TestOrchestratorInitialization:
    """Test SalesAgentOrchestrator initialization."""
    
    async def test_all_configs_loaded(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test all configs loaded (principles, situations, selector_rules, capture_schema)."""
        with patch('builtins.open', mock_open()) as mock_file:
            # Mock file reads
            def mock_read_side_effect(filename, mode='r'):
                config_name = os.path.basename(filename)
                if config_name in sample_configs:
                    return mock_open(read_data=json.dumps(sample_configs[config_name])).return_value
                return mock_open(read_data='{}').return_value
            
            mock_file.side_effect = mock_read_side_effect
            
            with patch('sales_agent.engine.orchestrator.LLMConnectionPool', return_value=mock_llm_pool):
                with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                    with patch('sales_agent.engine.orchestrator.LLMRouter', return_value=mock_llm_router):
                        with patch('sales_agent.engine.orchestrator.CaptureEngine'):
                            with patch('sales_agent.engine.orchestrator.SituationDetector'):
                                with patch('sales_agent.engine.orchestrator.ResponseGenerator'):
                                    orchestrator = SalesAgentOrchestrator()
                                    
                                    assert orchestrator.principles is not None
                                    assert orchestrator.situations is not None
                                    assert orchestrator.selector_rules is not None
                                    assert orchestrator.capture_schema is not None
    
    async def test_all_engines_initialized(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test all engines initialized."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = lambda f, m='r': mock_open(read_data='{}').return_value
            
            with patch('sales_agent.engine.orchestrator.LLMConnectionPool', return_value=mock_llm_pool):
                with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                    with patch('sales_agent.engine.orchestrator.LLMRouter', return_value=mock_llm_router):
                        with patch('sales_agent.engine.orchestrator.CaptureEngine') as mock_capture:
                            with patch('sales_agent.engine.orchestrator.SituationDetector') as mock_detect:
                                with patch('sales_agent.engine.orchestrator.ResponseGenerator') as mock_gen:
                                    orchestrator = SalesAgentOrchestrator()
                                    
                                    assert orchestrator.capture_engine is not None
                                    assert orchestrator.situation_detector is not None
                                    assert orchestrator.response_generator is not None
                                    assert orchestrator.principle_selector is not None
                                    assert orchestrator.response_builder is not None
    
    async def test_caches_initialized(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test caches initialized (exact + semantic)."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = lambda f, m='r': mock_open(read_data='{}').return_value
            
            with patch('sales_agent.engine.orchestrator.LLMConnectionPool', return_value=mock_llm_pool):
                with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                    with patch('sales_agent.engine.orchestrator.LLMRouter', return_value=mock_llm_router):
                        with patch('sales_agent.engine.orchestrator.CaptureEngine'):
                            with patch('sales_agent.engine.orchestrator.SituationDetector'):
                                with patch('sales_agent.engine.orchestrator.ResponseGenerator'):
                                    orchestrator = SalesAgentOrchestrator()
                                    
                                    assert orchestrator.exact_cache is not None
                                    assert orchestrator.semantic_cache is not None


@pytest.mark.asyncio
class TestSessionManagement:
    """Test session management."""
    
    async def test_new_session_creation(self, sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches):
        """Test new session creation."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches)
        
        session = orchestrator._get_or_create_session("new-session")
        
        assert "new-session" in orchestrator.sessions
        assert session == orchestrator.sessions["new-session"]
        assert "captured_context" in session
        assert "captured_quotes" in session
        assert "conversation_history" in session
        assert "principle_history" in session
        assert "resistance_count" in session
    
    async def test_existing_session_retrieval(self, sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches):
        """Test existing session retrieval."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches)
        
        # Create session
        session1 = orchestrator._get_or_create_session("existing-session")
        session1["captured_context"] = {"pain": "back pain"}
        
        # Retrieve same session
        session2 = orchestrator._get_or_create_session("existing-session")
        
        assert session1 == session2
        assert session2["captured_context"]["pain"] == "back pain"
    
    async def _create_orchestrator(self, sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches):
        """Helper to create orchestrator with mocks."""
        with patch('builtins.open', mock_open()) as mock_file:
            def mock_read_side_effect(filename, mode='r'):
                config_name = os.path.basename(filename)
                if config_name in sample_configs:
                    return mock_open(read_data=json.dumps(sample_configs[config_name])).return_value
                return mock_open(read_data='{}').return_value
            
            mock_file.side_effect = mock_read_side_effect
            
            with patch('sales_agent.engine.orchestrator.LLMConnectionPool', return_value=mock_llm_pool):
                with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                    with patch('sales_agent.engine.orchestrator.LLMRouter', return_value=mock_llm_router):
                        with patch('sales_agent.engine.orchestrator.CaptureEngine', return_value=mock_engines["capture"]):
                            with patch('sales_agent.engine.orchestrator.SituationDetector', return_value=mock_engines["detector"]):
                                with patch('sales_agent.engine.orchestrator.ResponseGenerator', return_value=mock_engines["generator"]):
                                    with patch('sales_agent.engine.orchestrator.ExactMatchCache', return_value=mock_caches["exact"]):
                                        with patch('sales_agent.engine.orchestrator.SemanticCache', return_value=mock_caches["semantic"]):
                                            return SalesAgentOrchestrator()


@pytest.mark.asyncio
class TestResistanceDetection:
    """Test resistance signal detection."""
    
    async def test_resistance_keyword_detection(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test resistance keyword detection."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router)
        
        is_resistance = orchestrator._detect_resistance_signals(
            message="I'm not interested",
            situation="price_shock_in_store",
            context={}
        )
        
        assert is_resistance is True
    
    async def test_resistance_objection_detection(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test objection in context detection."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router)
        
        is_resistance = orchestrator._detect_resistance_signals(
            message="Test",
            situation="price_shock_in_store",
            context={"objection": "price"}
        )
        
        assert is_resistance is True
    
    async def test_resistance_situation_detection(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test resistance situation detection."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router)
        
        is_resistance = orchestrator._detect_resistance_signals(
            message="Test",
            situation="price_shock_in_store",
            context={}
        )
        
        assert is_resistance is True  # price_shock_in_store is a resistance situation
    
    async def _create_orchestrator(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Helper to create orchestrator."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = lambda f, m='r': mock_open(read_data='{}').return_value
            
            with patch('sales_agent.engine.orchestrator.LLMConnectionPool', return_value=mock_llm_pool):
                with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                    with patch('sales_agent.engine.orchestrator.LLMRouter', return_value=mock_llm_router):
                        with patch('sales_agent.engine.orchestrator.CaptureEngine'):
                            with patch('sales_agent.engine.orchestrator.SituationDetector'):
                                with patch('sales_agent.engine.orchestrator.ResponseGenerator'):
                                    with patch('sales_agent.engine.orchestrator.ExactMatchCache'):
                                        with patch('sales_agent.engine.orchestrator.SemanticCache'):
                                            return SalesAgentOrchestrator()


@pytest.mark.asyncio
class TestReconcileLogic:
    """Test reconcile logic."""
    
    async def test_reconcile_triggered_low_confidence(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test reconcile triggered by low confidence (<0.7)."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router)
        
        situation_result = {"confidence": 0.5, "situation": "test"}
        capture_result = {"slots": {}}
        old_context = {}
        
        needs_reconcile = orchestrator._needs_reconcile(situation_result, capture_result, old_context)
        
        assert needs_reconcile is True
    
    async def test_reconcile_triggered_critical_slots(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test reconcile triggered by new critical slots."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router)
        
        situation_result = {"confidence": 0.9, "situation": "test"}
        capture_result = {"slots": {"pain": "back pain"}}  # pain is a critical slot
        old_context = {}
        
        needs_reconcile = orchestrator._needs_reconcile(situation_result, capture_result, old_context)
        
        assert needs_reconcile is True
    
    async def test_reconcile_triggered_significant_change(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test reconcile triggered by significant context change (>3 new slots)."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router)
        
        situation_result = {"confidence": 0.9, "situation": "test"}
        capture_result = {
            "slots": {
                "slot1": "value1",
                "slot2": "value2",
                "slot3": "value3",
                "slot4": "value4"  # 4 new slots > 3
            }
        }
        old_context = {}
        
        needs_reconcile = orchestrator._needs_reconcile(situation_result, capture_result, old_context)
        
        assert needs_reconcile is True
    
    async def test_no_reconcile_when_not_needed(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Test no reconcile when conditions not met."""
        orchestrator = await self._create_orchestrator(sample_configs, mock_llm_pool, mock_llm_router)
        
        situation_result = {"confidence": 0.9, "situation": "test"}
        capture_result = {"slots": {"non_critical": "value"}}
        old_context = {}
        
        needs_reconcile = orchestrator._needs_reconcile(situation_result, capture_result, old_context)
        
        assert needs_reconcile is False
    
    async def _create_orchestrator(self, sample_configs, mock_llm_pool, mock_llm_router):
        """Helper to create orchestrator."""
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = lambda f, m='r': mock_open(read_data='{}').return_value
            
            with patch('sales_agent.engine.orchestrator.LLMConnectionPool', return_value=mock_llm_pool):
                with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                    with patch('sales_agent.engine.orchestrator.LLMRouter', return_value=mock_llm_router):
                        with patch('sales_agent.engine.orchestrator.CaptureEngine'):
                            with patch('sales_agent.engine.orchestrator.SituationDetector'):
                                with patch('sales_agent.engine.orchestrator.ResponseGenerator'):
                                    with patch('sales_agent.engine.orchestrator.ExactMatchCache'):
                                        with patch('sales_agent.engine.orchestrator.SemanticCache'):
                                            return SalesAgentOrchestrator()


@pytest.mark.asyncio
class TestFullFlow:
    """Test full message processing flow."""
    
    async def test_exact_cache_hit_skips_processing(self, sample_configs, mock_llm_pool, mock_llm_router, mock_caches):
        """Test exact cache hit skips all processing."""
        cached_response = {
            "customer_facing": {"response": "Cached response"},
            "agent_dashboard": {"detection": {}}
        }
        mock_caches["exact"].get = MagicMock(return_value=cached_response)
        
        orchestrator = await self._create_full_orchestrator(sample_configs, mock_llm_pool, mock_llm_router, mock_caches)
        
        result = await orchestrator.process_message(
            session_id="test-session",
            customer_message="test message",
            product_context={}
        )
        
        assert result == cached_response
        # Verify engines were NOT called (cache hit)
        assert not hasattr(orchestrator.capture_engine, 'extract') or not orchestrator.capture_engine.extract.called
    
    async def test_full_flow_no_cache(self, sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches):
        """Test full flow: capture → detect → select → generate → build."""
        orchestrator = await self._create_full_orchestrator(sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches)
        
        result = await orchestrator.process_message(
            session_id="test-session",
            customer_message="This is too expensive",
            product_context={"name": "ErgoChair"}
        )
        
        # Verify response structure
        assert "customer_facing" in result
        assert "agent_dashboard" in result
        assert result["customer_facing"]["response"] == "I understand price is important to you."
        
        # Verify engines were called
        mock_engines["capture"].extract.assert_called_once()
        mock_engines["detector"].detect.assert_called()
        mock_engines["generator"].generate.assert_called_once()
        
        # Verify session state updated
        session = orchestrator.sessions["test-session"]
        assert "pain" in session["captured_context"]
        assert len(session["conversation_history"]) == 1
        assert len(session["principle_history"]) == 1
    
    async def test_session_state_persistence(self, sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches):
        """Test session state persists across calls."""
        orchestrator = await self._create_full_orchestrator(sample_configs, mock_llm_pool, mock_llm_router, mock_engines, mock_caches)
        
        # First call
        await orchestrator.process_message(
            session_id="test-session",
            customer_message="First message",
            product_context={}
        )
        
        session = orchestrator.sessions["test-session"]
        first_context = session["captured_context"].copy()
        first_history_len = len(session["conversation_history"])
        
        # Second call - context should accumulate
        await orchestrator.process_message(
            session_id="test-session",
            customer_message="Second message",
            product_context={}
        )
        
        session = orchestrator.sessions["test-session"]
        # Context should have accumulated
        assert len(session["captured_context"]) >= len(first_context)
        assert len(session["conversation_history"]) > first_history_len
    
    async def _create_full_orchestrator(self, sample_configs, mock_llm_pool, mock_llm_router, mock_caches, mock_engines=None):
        """Helper to create orchestrator with all mocks."""
        if mock_engines is None:
            mock_engines = {
                "capture": AsyncMock(),
                "detector": AsyncMock(),
                "generator": AsyncMock()
            }
            mock_engines["capture"].extract = AsyncMock(return_value={"slots": {}, "new_quotes": []})
            mock_engines["detector"].detect = AsyncMock(return_value={"situation": "test", "confidence": 0.9, "stage": "discovery"})
            mock_engines["generator"].generate = AsyncMock(return_value={"response": "Test response", "principle_used": "Test"})
        
        with patch('builtins.open', mock_open()) as mock_file:
            def mock_read_side_effect(filename, mode='r'):
                config_name = os.path.basename(filename)
                if config_name in sample_configs:
                    return mock_open(read_data=json.dumps(sample_configs[config_name])).return_value
                return mock_open(read_data='{}').return_value
            
            mock_file.side_effect = mock_read_side_effect
            
            with patch('sales_agent.engine.orchestrator.LLMConnectionPool', return_value=mock_llm_pool):
                with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                    with patch('sales_agent.engine.orchestrator.LLMRouter', return_value=mock_llm_router):
                        with patch('sales_agent.engine.orchestrator.CaptureEngine', return_value=mock_engines["capture"]):
                            with patch('sales_agent.engine.orchestrator.SituationDetector', return_value=mock_engines["detector"]):
                                with patch('sales_agent.engine.orchestrator.ResponseGenerator', return_value=mock_engines["generator"]):
                                    with patch('sales_agent.engine.orchestrator.ExactMatchCache', return_value=mock_caches["exact"]):
                                        with patch('sales_agent.engine.orchestrator.SemanticCache', return_value=mock_caches["semantic"]):
                                            return SalesAgentOrchestrator()

