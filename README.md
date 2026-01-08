# 🚀 DealCloser - AI Sales Agent Engine

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi)
![Pydantic](https://img.shields.io/badge/Pydantic-2.5-2D5C8F?style=for-the-badge)
![Uvicorn](https://img.shields.io/badge/Uvicorn-0.27-5E4F99?style=for-the-badge)

[![Tests](https://img.shields.io/badge/Tests-250%2B-green?style=for-the-badge&logo=pytest)](tests/)
[![Coverage](https://img.shields.io/badge/Coverage-Target_90%25-brightgreen?style=for-the-badge)](tests/)
[![Unit Tests](https://img.shields.io/badge/Unit_Tests-11_files-success?style=for-the-badge)](tests/unit/)
[![Integration Tests](https://img.shields.io/badge/Integration_Tests-11-passing?style=for-the-badge)](tests/)

[![Anthropic](https://img.shields.io/badge/Anthropic-Claude_4-FF7B72?style=for-the-badge&logo=anthropic)](https://anthropic.com)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT_4-412991?style=for-the-badge&logo=openai)](https://openai.com)
[![Async](https://img.shields.io/badge/Async-Await-3776ab?style=for-the-badge)](https://docs.python.org/3/library/asyncio.html)
[![HTTP/2](https://img.shields.io/badge/HTTP%2F2-Enabled-brightgreen?style=for-the-badge)](https://en.wikipedia.org/wiki/HTTP/2)


[Quick Start](#-quick-start) • [Features](#-features) • [Architecture](#-architecture) • [Testing](#-testing) • [Performance](#-performance) • [API](#-api-reference)

</div>

---

## 🧭 Simple Request Flow

```mermaid
flowchart TD
    Start[Customer Message] --> Cache{Cache Check}
    Cache -->|Hit| ReturnFast[Return Cached Response]
    Cache -->|Miss| Parallel[Capture and Detect in Parallel]
    Parallel --> Reconcile{Reconcile Needed}
    Reconcile -->|Yes| Redetect[Redetect with Updated Context]
    Reconcile -->|No| Match[Match Principle]
    Redetect --> Match
    Match --> Generate[Generate Response]
    Generate --> Return[Return Response]
```

## 🔍 Core Logic (Situation → Slots → Matching)

These diagrams describe the core decision engine: capture slots, detect situation, match principles, and generate responses. This is the heart of DealCloser.

### Core Logic Overview
```mermaid
flowchart TD
    Start[Customer Message] --> Capture[Capture Slots]
    Capture --> Context[Update Context]
    Context --> Detect[Detect Situation]
    Detect --> Match[Match Principle]
    Match --> Generate[Generate Response]
    Generate --> Return[Return Response]
```

### Situation Detection Path
```mermaid
flowchart TD
    Start[Message + Context] --> Signals[Extract Signals]
    Signals --> Classify[Classify Situation]
    Classify --> Confidence[Confidence Score]
    Confidence --> Decision{Reconcile Needed?}
    Decision -->|Yes| ReDetect[Re-detect with Updated Context]
    Decision -->|No| Done[Situation Locked]
    ReDetect --> Done
```

### Slot Capture and Context Update
```mermaid
flowchart TD
    Start[Message] --> Slots[Capture Slots]
    Slots --> Quotes[Capture Quotes]
    Quotes --> Merge[Merge into Context]
    Merge --> Persist[Persist Session State]
```

### Principle Matching
```mermaid
flowchart TD
    Start[Situation + Context] --> Rules[Rule Evaluation]
    Rules --> Match{Rule Match?}
    Match -->|Yes| Principle[Select Principle]
    Match -->|No| Fallback[Fallback Principle]
    Principle --> Response[Generate Response]
    Fallback --> Response
```

### Core Matching Logic (How Config Drives Decisions)

DealCloser is configuration-driven. The engine uses three inputs to decide the final response:

- **capture_schema.json**: Defines which slots to extract from messages (pain, budget_signal, objection, etc.). Captured slots and quotes update the session context.
- **situations.json**: Defines situations with signals and contra-signals. The detector scores situations against the current message + context and returns a winning situation and confidence.
- **principle_selector.json**: Defines rule-based mappings from situation + context to a principle. Rules are evaluated top-down, using `when_context_has` or `when_context_missing` to gate matches. If no rule matches, a fallback principle is used.

Simplified flow:
1. Capture slots from the message using `capture_schema.json`, then merge into session context.
2. Detect the most likely situation using `situations.json` signals and updated context.
3. Match a principle using `principle_selector.json` rules. If none match, use fallback.
4. Generate a response with the selected principle and the captured context.

## What is DealCloser?

DealCloser is a **production-ready AI sales agent engine** that transforms customer conversations into closing opportunities. It intelligently detects customer situations, selects proven sales principles from psychology research (Kahneman, Cialdini, Voss), and generates natural, human-like responses in milliseconds.


##  Quick Start

Get up and running in 3 minutes:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment variables
cat > .env << EOF
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional but recommended
EOF

# 3. Start the server
cd sales_agent
uvicorn api.main:app --reload

# 4. Test it out
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-001",
    "message": "This product is too expensive",
    "product_context": {"name": "ErgoChair", "price": 899}
  }'
```

**🎉 That's it!** Your AI sales agent is now running at `http://localhost:8000`

>  **Pro Tip**: Adding `OPENAI_API_KEY` enables multi-provider racing (lower latency) and semantic caching (higher hit rates)

>  **New to DealCloser?** Check out the **[Detailed Setup Guide](SETUP.md)** for step-by-step instructions, troubleshooting, and how to run the Streamlit UI.

---

##  Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Testing](#-testing)
- [API Reference](#-api-reference)
- [Performance](#-performance)
- [Configuration](#-configuration)
- [Development](#-development)

---

##  Features

###  Intelligent Situation Detection

Automatically detects customer situations (price objections, warranty concerns, comparison shopping, etc.) with high confidence scores.

###  Principle Selection Engine

Selects optimal sales principles based on:
- Detected situation
- Customer context (pain points, budget signals, emotional state)
- Conversation history (prevents repetition)
- Resistance tracking (adapts to customer pushback)

### Natural Response Generation

Generates human-like, empathetic responses that:
- Use customer's exact words (mirroring)
- Acknowledge concerns first
- Apply proven psychological principles
- Stay under 2 sentences (conversational)

### Performance Optimizations

| Optimization | Impact | Badge |
|-------------|--------|-------|
|  **Parallel Execution** | Target ~40% faster | ![Parallel](https://img.shields.io/badge/Parallel-Enabled-success?style=flat-square) |
| **Two-Tier Caching** | Target <10ms hits | ![Caching](https://img.shields.io/badge/Caching-2_Tiers-blue?style=flat-square) |
| **Multi-Provider Racing** | Target ~30% faster | ![Racing](https://img.shields.io/badge/Racing-Anthropic%2BOpenAI-purple?style=flat-square) |
| **Prompt Compression** | Target 50-60% tokens | ![Compression](https://img.shields.io/badge/Compression-50--60%25-orange?style=flat-square) |
| **Connection Pooling** | Target reduced latency | ![Pooling](https://img.shields.io/badge/Pooling-HTTP%2F2-brightgreen?style=flat-square) |
| **Tiered Model Routing** | Cost optimized | ![Routing](https://img.shields.io/badge/Routing-Tiered-yellow?style=flat-square) |

### Smart Reconcile Logic

Automatically re-runs situation detection when:
- Initial confidence is low (<0.7)
- Critical context is captured (pain, objection, budget)
- Significant new information arrives

### Comprehensive Monitoring

- Cache hit rates (exact + semantic)
- Provider win rates (Anthropic vs OpenAI)
- Reconcile statistics
- Per-step latency breakdown
- Session state tracking

---

## Architecture

### System Flow

```mermaid
flowchart TD
    Start[Customer Message] --> Cache{Cache Check}
    Cache -->|Hit| Fast["Fast Response under 10ms target"]
    Cache -->|Miss| Parallel[Parallel Execution]
    
    Parallel --> Capture[Capture Signals]
    Parallel --> Detect[Detect Situation]
    
    Capture --> Reconcile{Reconcile?}
    Detect --> Reconcile
    Reconcile -->|Yes| Redetect[Re-detect with Context]
    Reconcile -->|No| Select[Select Principle]
    Redetect --> Select
    
    Select --> Generate[Generate Response]
    Generate --> Store[Store in Caches]
    Store --> Return[Return Response]
    
    style Fast fill:#90EE90
    style Parallel fill:#87CEEB
    style Reconcile fill:#FFD700
```

### Additional Flows

#### ⚡ Cache Hit Path
```mermaid
flowchart TD
    Start[Customer Message] --> Exact{Exact Cache Hit?}
    Exact -->|Yes| ExactReturn[Return Cached Response]
    Exact -->|No| Semantic{Semantic Cache Hit?}
    Semantic -->|Yes| SemanticReturn[Return Cached Response]
    Semantic -->|No| Miss[Cache Miss Path]
```

#### Cache Miss + Reconcile Path
```mermaid
flowchart TD
    Start[Customer Message] --> Parallel[Capture + Detect Parallel]
    Parallel --> Update[Update Context]
    Update --> Reconcile{Reconcile Needed?}
    Reconcile -->|Yes| Redetect[Re-detect with Updated Context]
    Reconcile -->|No| Select[Select Principle]
    Redetect --> Select
    Select --> Generate[Generate Response]
    Generate --> Store[Store in Caches]
    Store --> Return[Return Response]
```

#### LLM Fallback Path
```mermaid
flowchart TD
    Start[Customer Message] --> Generate[Generate Response]
    Generate -->|Success| Return[Return Response]
    Generate -->|LLM Error| Fallback[Use Fallback Response]
    Fallback --> Return
```

### Core Components

```
🎯 Orchestrator (Brain)
├── 📊 Capture Engine (Extracts customer signals)
│   └── [![Slots](https://img.shields.io/badge/Slots-23-yellow?style=flat-square)]()
├── 🎯 Situation Detector (Classifies customer situation)
│   └── [![Situations](https://img.shields.io/badge/Situations-50%2B-purple?style=flat-square)]()
├── 🧠 Principle Selector (Selects best sales principle)
│   └── [![Principles](https://img.shields.io/badge/Principles-75%2B-orange?style=flat-square)]()
├── 💬 Response Generator (Creates natural responses)
│   └── [![Max_Sentences](https://img.shields.io/badge/Max_Sentences-2-red?style=flat-square)]()
└── 🏗️ Response Builder (Structures final output)

⚡ Performance Layer
├── 💾 ExactMatchCache (Exact duplicates)
│   └── [![TTL](https://img.shields.io/badge/TTL-3600s-blue?style=flat-square)]()
├── 🔍 SemanticCache (Similarity-based, embeddings)
│   └── [![Similarity](https://img.shields.io/badge/Similarity-0.92-green?style=flat-square)]()
├── 🚀 LLMRouter (Multi-provider racing)
│   └── [![Providers](https://img.shields.io/badge/Providers-2-purple?style=flat-square)]()
└── 🔌 LLMConnectionPool (HTTP/2 pooling)
    └── [![Connections](https://img.shields.io/badge/Connections-10--20-blue?style=flat-square)]()
```

### Request Journey

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant API
    participant Orchestrator
    participant Cache
    participant Engines
    participant LLMProviders as LLM Providers

    Customer->>API: POST /chat
    API->>Orchestrator: process_message()
    Orchestrator->>Cache: Check exact + semantic
    
    alt Cache Hit
        Cache-->>Orchestrator: Cached response under 10ms (target)
        Orchestrator-->>API: Response
        API-->>Customer: Instant response
    else Cache Miss
        par Parallel Execution
            Orchestrator->>Engines: Extract signals
            Orchestrator->>Engines: Detect situation
        end
        Orchestrator->>Orchestrator: Reconcile if needed
        Orchestrator->>Orchestrator: Select principle
        Orchestrator->>LLMProviders: Generate racing
        LLMProviders-->>Orchestrator: Response
        Orchestrator->>Cache: Store results
        Orchestrator-->>API: Response about 175ms (target)
        API-->>Customer: Natural response
    end
```

---

## Testing

DealCloser comes with **comprehensive test coverage** ensuring reliability and maintainability.

###  Test Structure


| Path | Purpose | Test Count |
|------|---------|------------|
| `tests/conftest.py` | Shared fixtures and mocks | N/A |
| `tests/test_validation_suite.py` | Integration tests | 11 |
| `tests/unit/test_capture.py` | Capture engine tests | 20 |
| `tests/unit/test_situation_detector.py` | Situation detection tests | 21 |
| `tests/unit/test_principle_selector.py` | Principle selector tests | 27 |
| `tests/unit/test_response_builder.py` | Response builder tests | 28 |
| `tests/unit/test_response_generator.py` | Response generator tests | 22 |
| `tests/unit/test_exact_cache.py` | Exact cache tests | 26 |
| `tests/unit/test_semantic_cache.py` | Semantic cache tests | 31 |
| `tests/unit/test_llm_router.py` | LLM router tests | 24 |
| `tests/unit/test_llm_pool.py` | LLM pool tests | 14 |
| `tests/unit/test_orchestrator.py` | Orchestrator tests | 15 |
| `tests/unit/test_utils.py` | Utility tests | 12 |

###  Running Tests

[![Run Tests](https://img.shields.io/badge/Run-pytest-blue?style=flat-square)](tests/)

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ --cov=sales_agent/engine --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_capture.py -v

# Run specific test
pytest tests/unit/test_principle_selector.py::TestRuleMatching::test_direct_situation_match -v

# Run with detailed output
pytest tests/unit/ -v -s

# Run fast tests only (skip slow ones)
pytest tests/unit/ -v -m "not slow"
```

###  Test Categories

| Category | Tests | Badge | Description |
|----------|-------|-------|-------------|
| **🔧 Pure Logic** | 94+ | [![Pure Logic](https://img.shields.io/badge/Pure_Logic-94%2B-blue?style=flat-square)]() | No external dependencies (cache, utils, selector, builder) |
| **🔌 Simple Mocks** | 65+ | [![Simple Mocks](https://img.shields.io/badge/Simple_Mocks-65%2B-yellow?style=flat-square)]() | External APIs mocked (semantic cache, pool, generator) |
| **🔄 Complex Logic** | 45+ | [![Complex Logic](https://img.shields.io/badge/Complex_Logic-45%2B-purple?style=flat-square)]() | Multi-component interactions (router, orchestrator) |
| **🤖 LLM-Dependent** | 50+ | [![LLM Tests](https://img.shields.io/badge/LLM_Dependent-50%2B-orange?style=flat-square)]() | LLM API interactions with mocks (capture, detector) |
| **🔗 Integration** | 11+ | [![Integration](https://img.shields.io/badge/Integration-11-green?style=flat-square)]() | End-to-end API flow tests |

### What's Tested



- All engine modules (capture, detect, select, generate)
- All utility modules (caching, pooling, routing)
- All LLM interactions (with comprehensive mocking)
- Error handling and fallback logic
- Edge cases and boundary conditions
- Statistics and monitoring
- Session state management
- Reconcile logic
- Multi-provider racing
- Cache hit/miss scenarios

###  Quality Assurance

Every component is tested for:
- **Correctness**: Does it work as expected?
- **Reliability**: Does it handle errors gracefully?
- **Performance**: Are edge cases optimized?
- **Maintainability**: Are tests readable and isolated?

---

##  API Reference

###  POST /chat


Send a customer message and get an AI-generated sales response.

**Request:**
```json
{
  "session_id": "customer-123",
  "message": "This product is too expensive. My back has been hurting for years.",
  "product_context": {
    "name": "ErgoChair Pro",
    "price": 899,
    "category": "office furniture"
  }
}
```

**Response:**
```json
{
  "customer_facing": {
    "response": "I understand price is really important to you, and it sounds like your back has been hurting for years. What if this chair could help you avoid future back pain and medical costs?"
  },
  "agent_dashboard": {
    "detection": {
      "customer_said": "This product is too expensive. My back has been hurting for years.",
      "detected_situation": "price_shock_in_store",
      "situation_confidence": 0.92,
      "micro_stage": "objection_handling",
      "detected_persona": "price_conscious",
      "persona_confidence": 0.85
    },
    "captured_context": {
      "pain": "back pain",
      "duration": "years",
      "objection": "price"
    },
    "captured_quotes": [
      "too expensive",
      "back has been hurting for years"
    ],
    "qualification_checklist": {
      "need_identified": true,
      "pain_expressed": true,
      "product_interest": false,
      "budget_discussed": true,
      "timeline_known": false,
      "decision_maker_known": false
    },
    "recommendation": {
      "principle": "Loss Aversion",
      "principle_id": "kahneman_loss_aversion_01",
      "source": "Kahneman, Thinking Fast and Slow, Ch.26, p.284",
      "approach": "Frame in terms of what they'll lose",
      "response": "I understand price is really important to you, and it sounds like your back has been hurting for years. What if this chair could help you avoid future back pain and medical costs?",
      "why_it_works": "Loss framing increases motivation"
    },
    "fallback": {
      "principle": "Loss Aversion",
      "principle_id": "kahneman_loss_aversion_01",
      "response": "I understand you mentioned 'back has been hurting for years'. Can you tell me more about what you're looking for?"
    },
    "next_probe": {
      "target": "product_interest",
      "question": "What features are most important to you?"
    },
    "session": {
      "session_id": "customer-123",
      "turn_count": 1,
      "resistance_count": 0,
      "principles_used": ["kahneman_loss_aversion_01"]
    },
    "system": {
      "latency_ms": 156,
      "step_latencies": {
        "cache_ms": 0,
        "capture_ms": 45,
        "detect_ms": 52,
        "detect_parallel_ms": 48,
        "reconcile_ms": 4,
        "select_ms": 1,
        "generate_ms": 54,
        "reconcile_triggered": true
      }
    },
    "cache_hit": false,
    "cache_type": null
  }
}
```

### GET /session/{session_id}

Get the full session state including conversation history.

**Response:**
```json
{
  "captured_context": {
    "pain": "back pain",
    "duration": "years"
  },
  "captured_quotes": [
    "too expensive",
    "back has been hurting"
  ],
  "conversation_history": [
    {
      "customer": "This product is too expensive",
      "agent": "I understand price is important..."
    }
  ],
  "principle_history": [
    "kahneman_loss_aversion_01"
  ],
  "resistance_count": 0
}
```

###  DELETE /session/{session_id}

Clear a session's state.

**Response:**
```json
{
  "status": "cleared"
}
```

### GET /cache/stats


Get cache statistics (exact + semantic).

**Response:**
```json
{
  "exact_cache": {
    "hits": 1250,
    "misses": 3750,
    "hit_rate": 0.25,
    "size": 892,
    "max_size": 1000,
    "ttl_seconds": 3600
  },
  "semantic_cache": {
    "hits": 210,
    "misses": 990,
    "hit_rate": 0.175,
    "embedding_computations": 1200,
    "size": 756,
    "max_size": 1000,
    "ttl_seconds": 3600,
    "similarity_threshold": 0.92,
    "enabled": true
  },
  "combined": {
    "exact_hits": 1250,
    "semantic_hits": 210,
    "exact_misses": 3750,
    "semantic_misses": 990,
    "total_hits": 1460,
    "total_requests": 5000
  }
}
```

### GET /reconcile/stats

Get reconcile statistics (how often parallel execution needs reconciliation).

**Response:**
```json
{
  "total_requests": 5000,
  "reconciles": 850,
  "reconcile_rate": 0.17
}
```

###  GET /llm/stats

Get LLM provider statistics (win rates, error rates for racing).

**Response:**
```json
{
  "anthropic": {
    "wins": 2850,
    "errors": 12,
    "total": 2862,
    "win_rate": 0.9958,
    "error_rate": 0.0042
  },
  "openai": {
    "wins": 2138,
    "errors": 8,
    "total": 2146,
    "win_rate": 0.9963,
    "error_rate": 0.0037
  }
}
```

### ❤️ GET /health

[![GET](https://img.shields.io/badge/METHOD-GET-green?style=flat-square)]()
[![Endpoint](https://img.shields.io/badge/Endpoint-/health-success?style=flat-square)]()

Health check endpoint with system status.

**Response:**
```json
{
  "status": "ok",
  "llm_connection": "ok",
  "config_loaded": true,
  "api_key_present": true
}
```

### 📍 GET /

[![GET](https://img.shields.io/badge/METHOD-GET-green?style=flat-square)]()
[![Endpoint](https://img.shields.io/badge/Endpoint-/-blue?style=flat-square)]()

Root endpoint with API information.

**Response:**
```json
{
  "message": "Sales Agent API",
  "endpoints": {
    "chat": "POST /chat",
    "get_session": "GET /session/{session_id}",
    "clear_session": "DELETE /session/{session_id}",
    "health": "GET /health"
  }
}
```

---

## Configuration

###  Configuration Files



Customize DealCloser by editing JSON files in `sales_agent/config/`:

| File | Purpose | Badge | Key Fields |
|------|---------|-------|------------|
| `principles.json` | Sales principles | [![Principles](https://img.shields.io/badge/Principles-75%2B-yellow?style=flat-square)]() | `principle_id`, `name`, `intervention`, `mechanism` |
| `situations.json` | Customer situations | [![Situations](https://img.shields.io/badge/Situations-50%2B-purple?style=flat-square)]() | `signals`, `stage`, `description` |
| `principle_selector.json` | Selection rules | [![Rules](https://img.shields.io/badge/Rules-27%2B-orange?style=flat-square)]() | `rules`, `fallback`, `when_context_has` |
| `capture_schema.json` | Extraction schema | [![Slots](https://img.shields.io/badge/Slots-23-blue?style=flat-square)]() | `slots`, `priority`, `listen_for` |
| `settings.py` | Environment config | [![Settings](https://img.shields.io/badge/Settings-Python-green?style=flat-square)]() | API keys, cache, retry, LLM configs |

### 🔧 Environment Variables

[![Env](https://img.shields.io/badge/Environment-Variables-blue?style=flat-square)]()
[![Required](https://img.shields.io/badge/Required-1-red?style=flat-square)]()
[![Optional](https://img.shields.io/badge/Optional-15%2B-yellow?style=flat-square)]()

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (enables racing + semantic cache)
OPENAI_API_KEY=sk-...

# Optional - Cache Configuration
CACHE_TTL_SECONDS=3600              # Default: 3600 (1 hour)
CACHE_MAX_SIZE=1000                 # Default: 1000
SEMANTIC_CACHE_SIMILARITY_THRESHOLD=0.92  # Default: 0.92

# Optional - Retry Configuration
RETRY_MAX_ATTEMPTS=3                # Default: 3
RETRY_BASE_DELAY_SECONDS=1.0        # Default: 1.0
RETRY_MAX_DELAY_SECONDS=10.0        # Default: 10.0

# Optional - LLM Configuration
LLM_TIMEOUT_SECONDS=30.0            # Default: 30.0
LLM_MAX_TOKENS_CAPTURE=500          # Default: 500
LLM_MAX_TOKENS_SITUATION=200        # Default: 200
LLM_MAX_TOKENS_RESPONSE=150         # Default: 150

# Optional - Connection Pool Configuration
HTTP_MAX_KEEPALIVE_CONNECTIONS=10   # Default: 10
HTTP_MAX_CONNECTIONS=20             # Default: 20

# Optional - Model Configuration
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MODEL_FAST=claude-sonnet-4-20250514
OPENAI_MODEL=gpt-4o
OPENAI_MODEL_FAST=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Optional - Orchestrator Configuration
RECONCILE_CONFIDENCE_THRESHOLD=0.7  # Default: 0.7
RECONCILE_NEW_SLOTS_THRESHOLD=3     # Default: 3
RECONCILE_NEW_QUOTES_THRESHOLD=1    # Default: 1

# Optional - Logging
LOG_LEVEL=INFO                       # Default: INFO (DEBUG, INFO, WARNING, ERROR)
```

###  Settings Management


Configuration is managed centrally via `sales_agent/config/settings.py`:

```python
from config.settings import config

# Access configuration
api_key = config.ANTHROPIC_API_KEY
cache_ttl = config.CACHE_TTL_SECONDS
log_level = config.LOG_LEVEL

# Validate required config
config.validate()  # Raises ValueError if ANTHROPIC_API_KEY missing

# Check if OpenAI enabled
if config.is_openai_enabled():
    # Use OpenAI features
    pass
```

---

## Development

### 📁 Project Structure


```
dealcloser/
├── sales_agent/
│   ├── api/
│   │   └── main.py              # FastAPI application
│   │       └── [![Endpoints](https://img.shields.io/badge/Endpoints-8-blue?style=flat-square)]()
│   ├── config/
│   │   ├── principles.json      # Sales principles
│   │   │   └── [![Principles](https://img.shields.io/badge/Principles-75%2B-yellow?style=flat-square)]()
│   │   ├── situations.json      # Customer situations
│   │   │   └── [![Situations](https://img.shields.io/badge/Situations-50%2B-purple?style=flat-square)]()
│   │   ├── principle_selector.json
│   │   │   └── [![Rules](https://img.shields.io/badge/Rules-27%2B-orange?style=flat-square)]()
│   │   ├── capture_schema.json
│   │   │   └── [![Slots](https://img.shields.io/badge/Slots-23-blue?style=flat-square)]()
│   │   └── settings.py          # Environment config
│   │       └── [![Settings](https://img.shields.io/badge/Settings-20%2B-green?style=flat-square)]()
│   └── engine/
│       ├── orchestrator.py      # Main orchestration logic
│       ├── capture.py           # Signal extraction
│       ├── situation_detector.py
│       ├── principle_selector.py
│       ├── response_generator.py
│       ├── response_builder.py
│       ├── exact_cache.py       # Exact-match caching
│       ├── semantic_cache.py    # Similarity-based caching
│       ├── llm_router.py        # Multi-provider racing
│       ├── llm_pool.py          # Connection pooling
│       └── utils.py             # Retry logic, helpers
├── tests/
│   ├── conftest.py              # Shared test fixtures
│   │   └── [![Fixtures](https://img.shields.io/badge/Fixtures-15%2B-yellow?style=flat-square)]()
│   ├── test_validation_suite.py # Integration tests
│   │   └── [![Integration](https://img.shields.io/badge/Tests-11-orange?style=flat-square)]()
│   └── unit/                    # 240+ unit tests
│       └── [![Unit Tests](https://img.shields.io/badge/Unit_Tests-240%2B-green?style=flat-square)]()
├── requirements.txt
│   └── [![Dependencies](https://img.shields.io/badge/Dependencies-15-blue?style=flat-square)]()
└── README.md
```

### Development Setup

[![Setup](https://img.shields.io/badge/Setup-Easy-green?style=flat-square)]()


```bash
# Clone and install
git clone <repo-url>
cd DealCloser
pip install -r requirements.txt

# Install dev dependencies (already in requirements.txt)
# pytest pytest-asyncio pytest-mock pytest-cov pytest-timeout

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/unit/ --cov=sales_agent/engine --cov-report=html

# Start FastAPI server (Terminal 1)
cd sales_agent
uvicorn api.main:app --reload

# Start Streamlit UI (Terminal 2 - in project root)
cd /path/to/DealCloser
streamlit run streamlit_app.py
```

>  **For detailed setup instructions, see [SETUP.md](SETUP.md)**

###  Code Quality


- **Linting**: Follow PEP 8 style guide
- **Type Hints**: Use type annotations
- **Docstrings**: Document all public functions
- **Tests**: Write tests for new features
- **Coverage**: Target 90%+ coverage

###  Config Details

- **capture_schema.json**: `version: 1.0`, `domain: retail_b2c`, **23 slots**
- **principle_selector.json**: `version: 1.0`, `domain: retail`, **27 rules**
- **principles.json**: **75+ principles** from Kahneman, Cialdini, Voss
- **situations.json**: **50+ situations** with signals and stages

---

<div align="center">

**Built with ❤️ for closing more deals**

[![GitHub](https://img.shields.io/badge/GitHub-Star_Us-black?style=for-the-badge&logo=github)](https://github.com/yourusername/dealcloser)
[![Issues](https://img.shields.io/badge/Issues-Report_Bug-red?style=for-the-badge)](https://github.com/yourusername/dealcloser/issues)
[![Features](https://img.shields.io/badge/Features-Request_Feature-green?style=for-the-badge)](https://github.com/yourusername/dealcloser/issues)

</div>
