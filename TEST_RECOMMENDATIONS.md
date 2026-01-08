# Unit Test Recommendations Summary

## Overview

Based on my analysis of your codebase, I've created a comprehensive unit test plan. You currently have **integration/validation tests** (`test_validation_suite.py`), but you're missing **unit tests** for individual components.

## Current Test Coverage

✅ **Integration Tests**: 10 validation tests covering end-to-end API flows
❌ **Unit Tests**: None (need to add)

## Critical Components That Need Unit Tests

### 🔴 High Priority (Core Logic)

1. **`principle_selector.py`** - Complex rule matching logic
   - **Why Critical**: Core business logic, handles principle selection rules
   - **Key Tests**: Rule matching, fallback logic, situation normalization, principle repetition prevention

2. **`exact_cache.py`** - Caching logic
   - **Why Critical**: Performance-critical, used for every request
   - **Key Tests**: Cache hit/miss, TTL expiration, eviction, stats

3. **`semantic_cache.py`** - Similarity-based caching
   - **Why Critical**: Performance optimization, similarity matching
   - **Key Tests**: Embedding generation, cosine similarity, threshold matching

4. **`llm_router.py`** - Multi-provider racing
   - **Why Critical**: Performance optimization, error handling, fallback logic
   - **Key Tests**: Racing logic, fallback when winner fails, tiered model selection, stats

5. **`orchestrator.py`** - Main orchestration flow
   - **Why Critical**: Coordinates all components, session management
   - **Key Tests**: Full flow, cache integration, reconcile logic, session state

### 🟡 Medium Priority (Supporting Logic)

6. **`response_builder.py`** - Response structure building
   - **Key Tests**: Response structure, persona detection, qualification checklist, next probe logic

7. **`response_generator.py`** - Response generation
   - **Key Tests**: Sentence validation (2-sentence limit), fallback responses, principle formatting

8. **`llm_pool.py`** - Connection pooling
   - **Key Tests**: Pool initialization, warmup, client reuse, connection management

9. **`utils.py`** - Retry logic
   - **Key Tests**: Exponential backoff, retry attempts, exception handling

### 🟢 Lower Priority (LLM-Dependent, Need Mocks)

10. **`capture.py`** - LLM-based extraction
    - **Key Tests**: Extraction logic, prompt compression, fallback handling
    - **Note**: Requires mocking LLM API calls

11. **`situation_detector.py`** - LLM-based detection
    - **Key Tests**: Detection logic, fallback handling, prompt compression
    - **Note**: Requires mocking LLM API calls

## Recommended Test Implementation Order

### Phase 1: Pure Logic (No Mocks Needed)
1. ✅ `exact_cache.py` - Straightforward cache logic
2. ✅ `utils.py` - Simple retry logic
3. ✅ `principle_selector.py` - Core business logic
4. ✅ `response_builder.py` - Response structure building

### Phase 2: Logic with Simple Mocks
5. ✅ `semantic_cache.py` - Mock embedding API
6. ✅ `llm_pool.py` - Mock HTTP client
7. ✅ `response_generator.py` - Mock LLM router

### Phase 3: Complex Logic
8. ✅ `llm_router.py` - Mock multiple LLM APIs, racing logic
9. ✅ `orchestrator.py` - Mock all engines, test full flow

### Phase 4: LLM-Dependent
10. ✅ `capture.py` - Mock LLM API
11. ✅ `situation_detector.py` - Mock LLM API

## Specific Test Cases to Prioritize

### 1. PrincipleSelector - Rule Matching
```python
def test_rule_match_with_context():
    """Test that rules match correctly when context conditions are met"""
    
def test_fallback_after_resistance():
    """Test that fallback principle is used after 2+ resistances"""
    
def test_principle_repetition_prevention():
    """Test that same principle isn't used 3+ times consecutively"""
    
def test_situation_normalization():
    """Test that rule situation names map to actual situation keys"""
```

### 2. ExactCache - Cache Behavior
```python
def test_cache_hit():
    """Test cache returns cached value on hit"""
    
def test_cache_expiration():
    """Test cache expires entries after TTL"""
    
def test_cache_eviction():
    """Test cache evicts oldest entry when max_size exceeded"""
    
def test_deterministic_key_generation():
    """Test same input always generates same key"""
```

### 3. LLMRouter - Racing Logic
```python
def test_single_provider_race():
    """Test racing with single provider (no race)"""
    
def test_multi_provider_race():
    """Test first completed provider wins"""
    
def test_fallback_on_winner_failure():
    """Test fallback to remaining providers when winner fails"""
    
def test_tiered_model_selection():
    """Test correct model selected based on complexity"""
```

### 4. Orchestrator - Full Flow
```python
def test_exact_cache_hit_skips_processing():
    """Test that exact cache hit skips all processing"""
    
def test_full_flow_no_cache():
    """Test full flow: capture → detect → reconcile → select → generate"""
    
def test_reconcile_triggered_by_critical_slots():
    """Test that reconcile is triggered when critical slots extracted"""
    
def test_session_state_persistence():
    """Test that session state persists across calls"""
```

### 5. ResponseBuilder - Response Structure
```python
def test_response_structure_complete():
    """Test that response has all required fields"""
    
def test_persona_detection():
    """Test persona detection based on signals and situation"""
    
def test_qualification_checklist():
    """Test qualification checklist built from context"""
    
def test_next_probe_priority():
    """Test next probe follows priority order"""
```

## Test Coverage Goals

- **Overall Unit Test Coverage: 90%+**
- **Critical Path Coverage: 100%** (orchestrator, principle_selector, caches)
- **Business Logic Coverage: 95%+** (principle selection, rule matching)
- **Edge Cases: 80%+** (errors, fallbacks, edge conditions)

## Missing Dependencies

Add these to `requirements.txt` for better testing:

```txt
pytest-mock>=3.12.0  # Better mocking support
pytest-cov>=4.1.0    # Coverage reporting
pytest-timeout>=2.2.0  # Test timeout handling
```

## Quick Start: Create Your First Unit Test

Here's a template for `tests/unit/test_exact_cache.py`:

```python
import pytest
import time
from sales_agent.engine.exact_cache import ExactMatchCache

@pytest.fixture
def cache():
    return ExactMatchCache(ttl_seconds=60, max_size=100)

def test_cache_miss(cache):
    """Test cache returns None on miss"""
    result = cache.get("test message", {})
    assert result is None
    assert cache.get_stats()["misses"] == 1

def test_cache_hit(cache):
    """Test cache returns cached value on hit"""
    response = {"response": "test"}
    cache.set("test message", {}, response)
    result = cache.get("test message", {})
    assert result == response
    assert cache.get_stats()["hits"] == 1

def test_cache_expiration(cache, mocker):
    """Test cache expires entries after TTL"""
    mocker.patch('time.time', return_value=0)
    cache.set("test message", {}, {"response": "test"})
    
    # Fast forward time past TTL
    mocker.patch('time.time', return_value=61)
    
    result = cache.get("test message", {})
    assert result is None
    assert cache.get_stats()["misses"] == 1

def test_deterministic_key_generation(cache):
    """Test same input always generates same key"""
    key1 = cache._make_key("test message", {"key": "value"})
    key2 = cache._make_key("test message", {"key": "value"})
    assert key1 == key2
    
    # Different order should still generate same key
    key3 = cache._make_key("test message", {"key": "value", "other": "data"})
    key4 = cache._make_key("test message", {"other": "data", "key": "value"})
    assert key3 == key4
```

## Next Steps

1. ✅ Review the comprehensive test plan in `UNIT_TEST_PLAN.md`
2. ✅ Add missing test dependencies to `requirements.txt`
3. ✅ Create `tests/unit/` directory structure
4. ✅ Start with Phase 1 tests (pure logic, no mocks)
5. ✅ Run tests with coverage: `pytest tests/unit/ --cov=sales_agent/engine --cov-report=html`
6. ✅ Set up CI/CD to run tests on every commit

## Benefits

- **Early Bug Detection**: Catch bugs before they reach production
- **Refactoring Confidence**: Safe to refactor with test coverage
- **Documentation**: Tests serve as living documentation
- **Regression Prevention**: Prevent bugs from reoccurring
- **Code Quality**: Forces better code structure (testable code)

