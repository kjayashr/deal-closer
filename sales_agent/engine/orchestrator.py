import json
import os
import sys
import time
import logging
import asyncio
from typing import Dict, Any, List

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import config
from .capture import CaptureEngine
from .situation_detector import SituationDetector
from .principle_selector import PrincipleSelector
from .response_generator import ResponseGenerator
from .response_builder import ResponseBuilder
from .llm_pool import LLMConnectionPool
from .exact_cache import ExactMatchCache
from .llm_router import LLMRouter
from .semantic_cache import SemanticCache

logger = logging.getLogger(__name__)

class SalesAgentOrchestrator:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to config directory relative to this file
            # orchestrator.py is in engine/, config/ is in sales_agent/
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(current_dir, "config")
        
        # Load all configs
        self.principles = self._load_json(os.path.join(config_path, "principles.json"))
        self.situations = self._load_json(os.path.join(config_path, "situations.json"))
        self.selector_rules = self._load_json(os.path.join(config_path, "principle_selector.json"))
        self.capture_schema = self._load_json(os.path.join(config_path, "capture_schema.json"))
        
        # Initialize shared connection pool
        self.llm_pool = LLMConnectionPool()
        
        # Initialize LLM router with racing (Phase 3)
        # Router uses the pool for Anthropic and adds OpenAI
        enable_openai = config.is_openai_enabled()
        self.llm_router = LLMRouter(llm_pool=self.llm_pool, enable_openai=enable_openai)
        
        # Initialize engines with router (Phase 3)
        # Engines will use router if available, fallback to pool/client
        self.capture_engine = CaptureEngine(self.capture_schema, llm_pool=self.llm_pool, llm_router=self.llm_router)
        self.situation_detector = SituationDetector(self.situations, llm_pool=self.llm_pool, llm_router=self.llm_router)
        self.principle_selector = PrincipleSelector(self.selector_rules, self.principles)
        self.response_generator = ResponseGenerator(self.principles, llm_pool=self.llm_pool, llm_router=self.llm_router)
        
        # Convert principles list to dict for response builder
        self.principles_dict = {p["principle_id"]: p for p in self.principles}
        self.response_builder = ResponseBuilder(self.principles_dict, self.capture_schema)
        
        # Initialize two-tier caching system
        # Tier 1: Exact-match cache (fastest, checked first)
        self.exact_cache = ExactMatchCache(
            ttl_seconds=config.CACHE_TTL_SECONDS,
            max_size=config.CACHE_MAX_SIZE
        )
        
        # Tier 2: Semantic cache (similarity-based, checked if exact misses)
        self.semantic_cache = SemanticCache(
            similarity_threshold=config.SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
            ttl_seconds=config.CACHE_TTL_SECONDS,
            max_size=config.CACHE_MAX_SIZE
        )
        
        # Legacy cache reference for backward compatibility
        self.cache = self.exact_cache
        
        # Session state
        self.sessions: Dict[str, Dict] = {}
        
        # Reconcile tracking for monitoring
        self.reconcile_stats = {
            "total_requests": 0,
            "reconciles": 0,
            "reconcile_rate": 0.0
        }
        
        # Critical slots that significantly affect situation detection
        # These trigger reconcile when newly extracted
        self.critical_slots = {
            "pain", "objection", "budget_signal", "emotional_state",
            "risk_concern", "trigger_event", "duration"
        }
    
    def _load_json(self, path: str) -> Dict:
        with open(path, 'r') as f:
            return json.load(f)
    
    def _get_or_create_session(self, session_id: str) -> Dict:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "captured_context": {},
                "captured_quotes": [],
                "conversation_history": [],
                "principle_history": [],
                "resistance_count": 0
            }
        return self.sessions[session_id]
    
    def _detect_resistance_signals(self, message: str, situation: str, context: Dict) -> bool:
        """Detect if customer message shows resistance signals."""
        resistance_keywords = [
            "no", "not interested", "don't want", "can't afford", "too expensive",
            "not sure", "maybe later", "need to think", "will come back",
            "let me think", "not today", "maybe next time", "not ready"
        ]
        
        message_lower = message.lower()
        has_resistance_keyword = any(keyword in message_lower for keyword in resistance_keywords)
        
        # Check for objection in context
        has_objection = context.get("objection") is not None
        
        # Check for negative emotional state
        emotional_state = context.get("emotional_state", "").lower()
        negative_emotions = ["worried", "anxious", "skeptical", "frustrated", "confused"]
        has_negative_emotion = any(emotion in emotional_state for emotion in negative_emotions)
        
        # Check situation type
        resistance_situations = [
            "price_shock_in_store", "walking_away_pause", "urgency_without_commitment",
            "budget_boundary", "fear_of_wrong_choice", "return_policy_anxiety"
        ]
        is_resistance_situation = situation in resistance_situations
        
        return has_resistance_keyword or has_objection or has_negative_emotion or is_resistance_situation
    
    def _detect_positive_signals(self, message: str, situation: str, context: Dict) -> bool:
        """Detect if customer message shows positive buying signals."""
        positive_keywords = [
            "yes", "sounds good", "i'll take it", "let's do it", "i want",
            "ready to buy", "when can i get", "how do i pay", "i'll buy"
        ]
        
        message_lower = message.lower()
        has_positive_keyword = any(keyword in message_lower for keyword in positive_keywords)
        
        # Check for commitment signal
        has_commitment = context.get("commitment_signal") is not None
        
        # Check for positive emotional state
        emotional_state = context.get("emotional_state", "").lower()
        positive_emotions = ["excited", "happy", "hopeful"]
        has_positive_emotion = any(emotion in emotional_state for emotion in positive_emotions)
        
        # Check situation type
        positive_situations = [
            "second_visit_return", "stock_availability_check", "delivery_timeline_concern"
        ]
        is_positive_situation = situation in positive_situations
        
        return has_positive_keyword or has_commitment or has_positive_emotion or is_positive_situation
    
    def _needs_reconcile(
        self,
        situation_result_pre: Dict[str, Any],
        capture_result: Dict[str, Any],
        old_context: Dict
    ) -> bool:
        """
        Determine if situation detection needs to be re-run with updated context.
        
        Reconcile triggers:
        1. Low confidence in initial detection (<threshold)
        2. Capture extracted new critical slots (pain, objection, budget_signal, etc.)
        3. Capture results significantly change context (many new slots added)
        
        Args:
            situation_result_pre: Initial situation detection result (with old context)
            capture_result: Capture extraction results
            old_context: Context before capture update (to compare against)
            
        Returns:
            True if reconcile is needed, False otherwise
        """
        # Trigger 1: Low confidence
        confidence = situation_result_pre.get("confidence", 0.5)
        if confidence < config.RECONCILE_CONFIDENCE_THRESHOLD:
            logger.debug(f"Reconcile triggered: low confidence ({confidence:.2f})")
            return True
        
        # Trigger 2: New critical slots extracted
        new_slots = capture_result.get("slots", {})
        old_context_keys = set(old_context.keys())
        new_slot_keys = set(new_slots.keys())
        newly_added_critical = (new_slot_keys - old_context_keys) & self.critical_slots
        
        if newly_added_critical:
            logger.debug(f"Reconcile triggered: new critical slots {newly_added_critical}")
            return True
        
        # Trigger 3: Significant context change (many new slots or many quotes)
        new_quotes = capture_result.get("new_quotes", [])
        num_new_slots = len(new_slot_keys - old_context_keys)
        
        # If more than threshold new slots or multiple new quotes, reconcile
        if num_new_slots > config.RECONCILE_NEW_SLOTS_THRESHOLD or len(new_quotes) > config.RECONCILE_NEW_QUOTES_THRESHOLD:
            logger.debug(f"Reconcile triggered: significant context change ({num_new_slots} new slots, {len(new_quotes)} quotes)")
            return True
        
        return False
    
    def _estimate_complexity(
        self,
        message: str,
        context: Dict,
        task_type: str = "general"
    ) -> str:
        """
        Estimate query complexity using heuristics.
        
        Args:
            message: Customer message
            context: Existing context dictionary
            task_type: Type of task (capture, detect, generate)
        
        Returns:
            Complexity level: "simple", "medium", or "complex"
        """
        # Heuristics for complexity detection
        word_count = len(message.split())
        context_richness = len([v for v in context.values() if v])
        
        # Check for multiple questions
        question_count = message.count("?")
        has_multiple_questions = question_count > 1
        
        # Check for complex vocabulary/patterns
        complex_indicators = [
            "compare", "difference", "between", "versus", "alternative",
            "detailed", "explain", "how does", "why does", "what makes",
            "specific", "particular", "requirements", "specifications"
        ]
        has_complex_vocab = any(indicator in message.lower() for indicator in complex_indicators)
        
        # Task-specific complexity adjustments
        if task_type == "generate":
            # Generation is generally more complex
            complexity_base = "medium"
        elif task_type == "capture":
            # Capture benefits from context richness
            complexity_base = "simple" if context_richness < config.COMPLEXITY_CONTEXT_RICHNESS_SIMPLE else "medium"
        else:
            # Detection is usually medium
            complexity_base = "medium"
        
        # Complexity scoring
        if word_count < config.COMPLEXITY_WORD_COUNT_SIMPLE and context_richness < config.COMPLEXITY_CONTEXT_RICHNESS_SIMPLE and not has_multiple_questions:
            return "simple"
        elif word_count > config.COMPLEXITY_WORD_COUNT_COMPLEX or has_multiple_questions or has_complex_vocab or context_richness > config.COMPLEXITY_CONTEXT_RICHNESS_COMPLEX:
            return "complex"
        else:
            return complexity_base
    
    async def process_message(
        self, 
        session_id: str, 
        customer_message: str,
        product_context: Dict = None
    ) -> Dict[str, Any]:
        
        # Start latency tracking
        start_time = time.time()
        
        session = self._get_or_create_session(session_id)
        
        # Two-tier caching: Exact match first, then semantic similarity
        cache_key_context = session["captured_context"].copy()
        cache_start = time.time()
        
        # Tier 1: Check exact-match cache (fastest)
        cached_response = self.exact_cache.get(customer_message, cache_key_context)
        if cached_response:
            logger.info("Exact cache hit")
            cache_latency_ms = int((time.time() - cache_start) * 1000)
            agent_dashboard = cached_response.setdefault("agent_dashboard", {})
            system_info = agent_dashboard.setdefault("system", {})
            system_info["latency_ms"] = cache_latency_ms
            step_latencies = system_info.setdefault("step_latencies", {})
            step_latencies["cache_ms"] = cache_latency_ms
            agent_dashboard["cache_hit"] = True
            agent_dashboard["cache_type"] = "exact"
            logger.info(
                "Cache response latency_ms=%s session_id=%s cache_type=exact",
                cache_latency_ms,
                session_id
            )
            return cached_response
        
        # Tier 2: Check semantic cache (similarity-based)
        cached_response = await self.semantic_cache.get(customer_message, cache_key_context)
        if cached_response:
            logger.info("Semantic cache hit")
            cache_latency_ms = int((time.time() - cache_start) * 1000)
            agent_dashboard = cached_response.setdefault("agent_dashboard", {})
            system_info = agent_dashboard.setdefault("system", {})
            system_info["latency_ms"] = cache_latency_ms
            step_latencies = system_info.setdefault("step_latencies", {})
            step_latencies["cache_ms"] = cache_latency_ms
            agent_dashboard["cache_hit"] = True
            agent_dashboard["cache_type"] = "semantic"
            logger.info(
                "Cache response latency_ms=%s session_id=%s cache_type=semantic",
                cache_latency_ms,
                session_id
            )
            return cached_response
        
        # Track total requests for reconcile stats
        self.reconcile_stats["total_requests"] += 1
        
        # Step 1 & 2: Parallel Capture + Detect (Phase 2 optimization)
        # Pass 1: Run Capture and Detect in parallel (Detect uses pre-capture context)
        capture_start = time.time()
        detect_start = time.time()
        
        # Store old context for parallel detect
        old_context = session["captured_context"].copy()
        
        # Run both in parallel
        capture_result, situation_result_pre = await asyncio.gather(
            self.capture_engine.extract(
                message=customer_message,
                existing_context=old_context
            ),
            self.situation_detector.detect(
                message=customer_message,
                context=old_context  # Use old context for parallel execution
            )
        )
        
        capture_latency_ms = int((time.time() - capture_start) * 1000)
        detect_parallel_latency_ms = int((time.time() - detect_start) * 1000)
        
        # Check if reconcile is needed BEFORE updating context (need old context for comparison)
        reconcile_start = time.time()
        needs_reconcile = self._needs_reconcile(situation_result_pre, capture_result, old_context)
        
        # Update context with capture results
        session["captured_context"].update(capture_result["slots"])
        session["captured_quotes"].extend(capture_result.get("new_quotes", []))
        
        if needs_reconcile:
            # Re-run Detect with updated context
            logger.info("Reconcile triggered - re-running situation detection with updated context")
            self.reconcile_stats["reconciles"] += 1
            situation_result = await self.situation_detector.detect(
                message=customer_message,
                context=session["captured_context"]  # Use updated context
            )
            reconcile_latency_ms = int((time.time() - reconcile_start) * 1000)
            detect_latency_ms = detect_parallel_latency_ms + reconcile_latency_ms
            logger.debug(f"Reconcile completed: {reconcile_latency_ms}ms")
        else:
            # Use parallel result
            situation_result = situation_result_pre
            detect_latency_ms = detect_parallel_latency_ms
            reconcile_latency_ms = 0
        
        # Update reconcile stats
        self.reconcile_stats["reconcile_rate"] = (
            self.reconcile_stats["reconciles"] / self.reconcile_stats["total_requests"]
            if self.reconcile_stats["total_requests"] > 0 else 0.0
        )
        
        # Track resistance count
        if self._detect_resistance_signals(customer_message, situation_result["situation"], session["captured_context"]):
            session["resistance_count"] += 1
        elif self._detect_positive_signals(customer_message, situation_result["situation"], session["captured_context"]):
            # Reset resistance count on positive signals
            session["resistance_count"] = 0
        
        # Step 3: Select Principle
        select_start = time.time()
        principle_result = self.principle_selector.select(
            situation=situation_result["situation"],
            context=session["captured_context"],
            principle_history=session["principle_history"],
            resistance_count=session["resistance_count"]
        )
        
        # Get fallback principle
        fallback_principle = self.principle_selector.get_fallback_principle(
            resistance_count=session["resistance_count"],
            context=session["captured_context"]
        )
        select_latency_ms = int((time.time() - select_start) * 1000)
        
        # Step 4: Generate Response
        generate_start = time.time()
        # Estimate complexity for generation (Phase 5)
        generate_complexity = self._estimate_complexity(
            customer_message,
            session["captured_context"],
            "generate"
        )
        response_result = await self.response_generator.generate(
            principle=principle_result["principle"],
            customer_quotes=session["captured_quotes"][-config.RESPONSE_MAX_QUOTES:],  # Last N quotes
            situation=situation_result["situation"],
            context=session["captured_context"],
            product_context=product_context,
            complexity=generate_complexity
        )
        generate_latency_ms = int((time.time() - generate_start) * 1000)
        
        # Calculate total latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Per-step latency breakdown
        step_latencies = {
            "cache_ms": 0,
            "capture_ms": capture_latency_ms,
            "detect_ms": detect_latency_ms,
            "detect_parallel_ms": detect_parallel_latency_ms,
            "reconcile_ms": reconcile_latency_ms if needs_reconcile else 0,
            "select_ms": select_latency_ms,
            "generate_ms": generate_latency_ms,
            "reconcile_triggered": needs_reconcile
        }
        
        # Calculate turn count
        turn_count = len(session["conversation_history"]) + 1
        
        # Update session
        session["conversation_history"].append({
            "customer": customer_message,
            "agent": response_result["response"]
        })
        session["principle_history"].append(principle_result["principle"]["principle_id"])
        
        # Build recommendation dict with response
        recommendation = {
            "principle": principle_result["principle"],
            "response": response_result["response"]
        }
        
        # Build structured response using ResponseBuilder
        structured_response = self.response_builder.build(
            customer_message=customer_message,
            customer_facing_response=response_result["response"],
            detection_result=situation_result,
            captured_context=session["captured_context"],
            captured_quotes=session["captured_quotes"],
            recommendation=recommendation,
            fallback_principle=fallback_principle,
            session_id=session_id,
            turn_count=turn_count,
            resistance_count=session["resistance_count"],
            principles_used=session["principle_history"],
            latency_ms=latency_ms,
            step_latencies=step_latencies
        )
        
        # Cache the response in both caches
        # Use same context as cache lookup - before capture updates
        self.exact_cache.set(customer_message, cache_key_context, structured_response)
        await self.semantic_cache.set(customer_message, cache_key_context, structured_response)
        
        structured_response["agent_dashboard"]["cache_hit"] = False
        structured_response["agent_dashboard"]["cache_type"] = None
        logger.info(
            "Request completed latency_ms=%s session_id=%s turn_count=%s step_latencies=%s",
            latency_ms,
            session_id,
            turn_count,
            step_latencies
        )
        
        return structured_response
    
    async def close(self):
        """Cleanup resources on shutdown."""
        await self.llm_pool.close()
