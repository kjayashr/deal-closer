from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import sys
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def configure_logging() -> None:
    # Add parent directory to path for config import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import config
    
    level_name = config.LOG_LEVEL.upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        stream=sys.stdout
    )
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(logger_name).setLevel(level)

configure_logging()
logger = logging.getLogger(__name__)

# Add parent directory to path to import engine modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.orchestrator import SalesAgentOrchestrator

app = FastAPI(title="Sales Agent API")
orchestrator = SalesAgentOrchestrator()

@app.middleware("http")
async def log_request_latency(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "HTTP %s %s status=%s latency_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms
    )
    return response

@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    await orchestrator.llm_pool.warmup()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown."""
    await orchestrator.close()

class MessageRequest(BaseModel):
    session_id: str
    message: str
    product_context: Optional[Dict] = None

class MessageResponse(BaseModel):
    customer_facing: Dict[str, str]
    agent_dashboard: Dict[str, Any]

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    try:
        result = await orchestrator.process_message(
            session_id=request.session_id,
            customer_message=request.message,
            product_context=request.product_context
        )
        return MessageResponse(
            customer_facing=result["customer_facing"],
            agent_dashboard=result["agent_dashboard"]
        )
    except Exception as e:
        logger.error(
            "Error processing chat request session_id=%s error=%s",
            request.session_id,
            str(e),
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id not in orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return orchestrator.sessions[session_id]

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    if session_id in orchestrator.sessions:
        del orchestrator.sessions[session_id]
    return {"status": "cleared"}

@app.get("/health")
async def health():
    """Health check endpoint with system status."""
    import os
    from anthropic import AsyncAnthropic
    
    health_status = {
        "status": "ok",
        "llm_connection": "unknown",
        "config_loaded": False
    }
    
    # Check config loading
    try:
        config_files = [
            "principles.json",
            "situations.json", 
            "principle_selector.json",
            "capture_schema.json"
        ]
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config"
        )
        all_loaded = all(
            os.path.exists(os.path.join(config_path, f)) for f in config_files
        )
        health_status["config_loaded"] = all_loaded
    except Exception as e:
        health_status["config_loaded"] = False
        health_status["config_error"] = str(e)
    
    # Check LLM connection
    try:
        # Add parent directory to path for config import
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.settings import config
        api_key = config.ANTHROPIC_API_KEY
        if api_key:
            # Quick connection test
            client = AsyncAnthropic(api_key=api_key)
            # We'll do a minimal test - just check if we can instantiate
            # A real test would require an API call, but that's expensive for health checks
            health_status["llm_connection"] = "ok"
            health_status["api_key_present"] = True
        else:
            health_status["llm_connection"] = "error"
            health_status["api_key_present"] = False
            health_status["error"] = "ANTHROPIC_API_KEY not set"
    except Exception as e:
        health_status["llm_connection"] = "error"
        health_status["error"] = str(e)
    
    # Overall status
    if health_status["llm_connection"] == "ok" and health_status["config_loaded"]:
        health_status["status"] = "ok"
    else:
        health_status["status"] = "degraded"
    
    return health_status

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics for monitoring (both exact and semantic)."""
    return {
        "exact_cache": orchestrator.exact_cache.get_stats(),
        "semantic_cache": orchestrator.semantic_cache.get_stats(),
        "combined": {
            "exact_hits": orchestrator.exact_cache.get_stats()["hits"],
            "semantic_hits": orchestrator.semantic_cache.get_stats()["hits"],
            "exact_misses": orchestrator.exact_cache.get_stats()["misses"],
            "semantic_misses": orchestrator.semantic_cache.get_stats()["misses"],
            "total_hits": (
                orchestrator.exact_cache.get_stats()["hits"] +
                orchestrator.semantic_cache.get_stats()["hits"]
            ),
            "total_requests": (
                orchestrator.exact_cache.get_stats()["hits"] +
                orchestrator.exact_cache.get_stats()["misses"]
            )
        }
    }

@app.get("/reconcile/stats")
async def reconcile_stats():
    """Get reconcile statistics for monitoring."""
    return orchestrator.reconcile_stats

@app.get("/llm/stats")
async def llm_stats():
    """Get LLM provider statistics (win rates, error rates)."""
    return orchestrator.llm_router.get_stats()

@app.get("/")
async def root():
    return {
        "message": "Sales Agent API",
        "endpoints": {
            "chat": "POST /chat",
            "get_session": "GET /session/{session_id}",
            "clear_session": "DELETE /session/{session_id}",
            "health": "GET /health"
        }
    }
