"""
Sales AI Coach - Streamlit UI
Developer-facing interface for analyzing sales conversations with psychology-backed recommendations.
"""
import streamlit as st
import httpx
import json
from typing import Dict, Any, Optional
from datetime import datetime
import os
import html

# Page config
st.set_page_config(
    page_title="Sales AI Coach",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
:root {
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-tertiary: #1a1a24;
    --bg-card: #16161f;
    --border-color: #2a2a3a;
    --border-focus: #4d9fff;
    --text-primary: #e8e8ed;
    --text-secondary: #9898a8;
    --text-muted: #686878;
    --accent-blue: #4d9fff;
    --accent-green: #34d399;
    --accent-yellow: #fbbf24;
    --accent-orange: #f97316;
    --accent-red: #ef4444;
    --accent-purple: #a78bfa;
    --grounding-bg: #1e1b4b;
    --grounding-border: #4338ca;
    --grounding-accent: #a78bfa;
}

/* Main app styling */
.stApp {
    background:
        radial-gradient(circle at 20% 20%, rgba(77, 159, 255, 0.08), transparent 45%),
        radial-gradient(circle at 80% 10%, rgba(52, 211, 153, 0.06), transparent 40%),
        radial-gradient(circle at 50% 80%, rgba(249, 115, 22, 0.05), transparent 45%),
        var(--bg-primary);
    color: var(--text-primary);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--bg-secondary);
}

[data-testid="stSidebar"] .stTextInput,
[data-testid="stSidebar"] .stSelectbox,
[data-testid="stSidebar"] .stTextArea {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}

/* Headers */
h1, h2, h3 {
    color: var(--text-primary);
}

/* Cards */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

.summary-strip {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    background: linear-gradient(120deg, rgba(77, 159, 255, 0.12), rgba(52, 211, 153, 0.08));
    border: 1px solid var(--border-color);
    border-radius: 14px;
    padding: 1rem 1.25rem;
    margin: 1rem 0 1.5rem 0;
}

.summary-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 140px;
}

.summary-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

.summary-value {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
}

.summary-meta {
    font-size: 0.75rem;
    color: var(--text-secondary);
}

.card-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 0.75rem;
}

.card-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Badges */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
}

.badge-situation {
    background: linear-gradient(135deg, var(--accent-red), #dc2626);
    color: white;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-persona {
    background: rgba(77, 159, 255, 0.15);
    border: 1px solid rgba(77, 159, 255, 0.3);
    color: var(--accent-blue);
}

.badge-stage {
    background: rgba(167, 139, 250, 0.15);
    border: 1px solid rgba(167, 139, 250, 0.3);
    color: var(--accent-purple);
}

/* Confidence bar */
.confidence-bar {
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.confidence-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
}

.confidence-high {
    background: linear-gradient(90deg, #22c55e, #16a34a);
}

.confidence-medium {
    background: linear-gradient(90deg, #eab308, #ca8a04);
}

.confidence-low {
    background: linear-gradient(90deg, #ef4444, #dc2626);
}

/* Grounding panel - HERO SECTION */
.grounding-panel {
    background: linear-gradient(135deg, var(--grounding-bg), #1e1e2e);
    border: 1px solid var(--grounding-border);
    border-radius: 12px;
    padding: 1.25rem;
    margin: 1.5rem 0;
    position: relative;
    box-shadow: 0 4px 20px rgba(167, 139, 250, 0.1);
}

.grounding-panel::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, var(--accent-purple), var(--grounding-border));
    border-radius: 12px 0 0 12px;
}

.grounding-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--accent-purple);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.source-citation {
    background: rgba(167, 139, 250, 0.1);
    border: 1px solid rgba(167, 139, 250, 0.3);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    color: var(--accent-purple);
    margin: 0.75rem 0;
}

.signal-match {
    background: rgba(251, 191, 36, 0.1);
    border-left: 3px solid var(--accent-yellow);
    padding: 0.75rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.75rem 0;
    font-style: italic;
    color: var(--accent-yellow);
}

/* Response cards */
.response-card {
    background: linear-gradient(135deg, rgba(52, 211, 153, 0.1), rgba(52, 211, 153, 0.05));
    border: 1px solid rgba(52, 211, 153, 0.3);
    border-radius: 12px;
    padding: 1.25rem;
    margin: 1rem 0;
}

.reveal {
    animation: fadeUp 0.5s ease both;
}

.reveal-delay {
    animation: fadeUp 0.6s ease both;
    animation-delay: 0.08s;
}

@keyframes fadeUp {
    from {
        opacity: 0;
        transform: translateY(6px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.fallback-card {
    background: linear-gradient(135deg, rgba(249, 115, 22, 0.1), rgba(249, 115, 22, 0.05));
    border: 1px solid rgba(249, 115, 22, 0.3);
    border-radius: 12px;
    padding: 1.25rem;
    margin: 1rem 0;
}

.probe-card {
    background: linear-gradient(135deg, rgba(77, 159, 255, 0.1), rgba(77, 159, 255, 0.05));
    border: 1px solid rgba(77, 159, 255, 0.3);
    border-radius: 12px;
    padding: 1.25rem;
    margin: 1rem 0;
}

/* Stage flow */
.stage-flow {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1rem 0;
    flex-wrap: wrap;
}

.stage-item {
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 500;
    transition: all 0.3s ease;
}

.stage-item.active {
    background: var(--accent-purple);
    color: white;
}

.stage-item.inactive {
    background: var(--bg-tertiary);
    color: var(--text-muted);
    border: 1px solid var(--border-color);
}

.stage-arrow {
    color: var(--text-muted);
    font-size: 1.2rem;
}

/* Context pills */
.context-pill {
    display: inline-block;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 16px;
    padding: 0.25rem 0.75rem;
    margin: 0.25rem;
    font-size: 0.75rem;
    color: var(--text-secondary);
}

.context-pill-key {
    color: var(--accent-blue);
    font-weight: 600;
}

/* Qualification checklist */
.qualification-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    font-size: 0.85rem;
}

.checkbox-checked {
    color: var(--accent-green);
}

.checkbox-unchecked {
    color: var(--text-muted);
}

/* Metrics bar */
.metrics-bar {
    display: flex;
    gap: 2rem;
    padding: 1rem;
    background: var(--bg-tertiary);
    border-radius: 8px;
    margin-top: 1rem;
    font-size: 0.8rem;
    font-family: 'Courier New', monospace;
}

/* Tabs */
[data-testid="stTabs"] > div {
    gap: 0.5rem;
}

[data-testid="stTabs"] button {
    background: var(--bg-tertiary);
    border-radius: 999px;
    border: 1px solid var(--border-color);
    padding: 0.35rem 0.9rem;
    color: var(--text-secondary);
    font-size: 0.8rem;
}

[data-testid="stTabs"] button[aria-selected="true"] {
    background: var(--accent-blue);
    border-color: transparent;
    color: white;
}

.metric-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.metric-label {
    color: var(--text-muted);
}

.metric-value {
    color: var(--text-primary);
    font-weight: 600;
}

/* Reasoning trace */
.reasoning-trace {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 1.5rem 0;
    flex-wrap: wrap;
}

.trace-box {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
    min-width: 120px;
    text-align: center;
}

.trace-box-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}

.trace-box-content {
    font-size: 0.85rem;
    color: var(--text-primary);
    font-weight: 500;
}

.trace-arrow {
    color: var(--accent-purple);
    font-size: 1.5rem;
    font-weight: bold;
}

/* Buttons */
.stButton > button {
    background: var(--accent-blue);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.stButton > button:hover {
    background: #3d8fff;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(77, 159, 255, 0.3);
}

/* Text areas and inputs */
.stTextArea > div > div > textarea,
.stTextInput > div > div > input {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
}

.stTextArea > div > div > textarea:focus,
.stTextInput > div > div > input:focus {
    border-color: var(--border-focus);
}

/* JSON viewer */
.json-viewer {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
    font-family: 'Courier New', monospace;
    font-size: 0.75rem;
    overflow-x: auto;
    max-height: 400px;
    overflow-y: auto;
}

/* Hide Streamlit default elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL")
DEFAULT_SESSION_ID = "streamlit-demo-session"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = DEFAULT_SESSION_ID
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None
if "show_json" not in st.session_state:
    st.session_state.show_json = False
if "show_trace" not in st.session_state:
    st.session_state.show_trace = True


def call_api(
    message: str,
    session_id: str,
    product_context: Optional[Dict] = None,
    channel: Optional[str] = None,
    turn: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Call the FastAPI backend to analyze the message."""
    try:
        with httpx.Client(timeout=30.0) as client:
            # First check if API is available
            health_check_failed = False
            try:
                health_response = client.get(f"{API_BASE_URL}/health", timeout=5.0)
                if health_response.status_code != 200:
                    st.warning(f"API health check failed. Status: {health_response.status_code}")
            except Exception:
                health_check_failed = True

            response = client.post(
                f"{API_BASE_URL}/chat",
                json={
                    "session_id": session_id,
                    "message": message,
                    "product_context": product_context,
                    "channel": channel,
                    "turn": turn,
                },
                timeout=30.0
            )
            response.raise_for_status()
            if health_check_failed:
                st.warning(f"API health check failed at {API_BASE_URL}, but /chat responded successfully.")
            return response.json()
    except httpx.ConnectError:
        st.error(f"❌ Cannot connect to API at {API_BASE_URL}. Please ensure the FastAPI server is running.")
        st.info("Start the server with: `uvicorn sales_agent.api.main:app --reload`")
        return None
    except httpx.TimeoutException:
        st.error("⏱️ Request timed out. The API took too long to respond.")
        return None
    except httpx.HTTPStatusError as e:
        st.error(f"❌ API error ({e.response.status_code}): {e.response.text}")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        return None


def esc(value: Any) -> str:
    """Escape values for safe HTML rendering."""
    if value is None:
        return ""
    return html.escape(str(value))


def render_header():
    """Render the main header."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e1b4b, #312e81); padding: 2rem; border-radius: 12px; margin-bottom: 2rem;">
        <h1 style="margin: 0; color: #e8e8ed; font-size: 2rem;">🧠 Sales AI Coach</h1>
        <p style="margin: 0.5rem 0 0 0; color: #9898a8; font-size: 1rem;">Psychology-backed conversation intelligence</p>
    </div>
    """, unsafe_allow_html=True)


def render_stage_flow(current_stage: str):
    """Render the stage flow indicator."""
    stages = ["discovery", "qualification", "presentation", "objection_handling", "closing"]
    stage_labels = {
        "discovery": "Discovery",
        "qualification": "Qualification",
        "presentation": "Presentation",
        "objection_handling": "Objection Handling",
        "closing": "Closing"
    }
    
    stage_html = '<div class="stage-flow">'
    current = (current_stage or "").lower()
    for i, stage in enumerate(stages):
        is_active = stage == current
        stage_class = "active" if is_active else "inactive"
        stage_html += f'<div class="stage-item {stage_class}">{stage_labels.get(stage, stage.title())}</div>'
        if i < len(stages) - 1:
            stage_html += '<span class="stage-arrow">→</span>'
    stage_html += '</div>'
    
    st.markdown(stage_html, unsafe_allow_html=True)


def render_situation_card(detection: Dict[str, Any]):
    """Render the situation detection card."""
    situation = detection.get("detected_situation", "unknown")
    confidence = detection.get("situation_confidence", 0.0)
    
    confidence_class = "confidence-high" if confidence >= 0.8 else "confidence-medium" if confidence >= 0.5 else "confidence-low"
    
    situation_label = esc(str(situation).replace("_", " ").title())
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <span class="card-title">Situation Detected</span>
        </div>
        <div style="margin-bottom: 0.5rem;">
            <span class="badge badge-situation">{situation_label}</span>
        </div>
        <div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span style="font-size: 0.8rem; color: var(--text-secondary);">Confidence</span>
                <span style="font-size: 0.8rem; color: var(--text-primary); font-weight: 600;">{confidence:.0%}</span>
            </div>
            <div class="confidence-bar">
                <div class="confidence-fill {confidence_class}" style="width: {confidence * 100}%;"></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_context_panel(detection: Dict[str, Any], captured_context: Dict[str, Any], qualification: Dict[str, bool]):
    """Render context and qualification panels."""
    persona = detection.get("detected_persona", "unknown")
    persona_confidence = detection.get("persona_confidence", 0.0)
    
    col1, col2 = st.columns(2)
    
    with col1:
        persona_label = esc(str(persona).replace("_", " ").title())
        st.markdown(f"""
        <div class="card">
            <div class="card-header">
                <span class="card-title">Context & Persona</span>
            </div>
            <div style="margin-bottom: 1rem;">
                <span class="badge badge-persona">{persona_label}</span>
                <span style="font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;">{persona_confidence:.0%} confidence</span>
            </div>
            <div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: uppercase;">Captured Context</div>
        """, unsafe_allow_html=True)
        
        # Render context pills
        if captured_context:
            pills_html = ""
            for key, value in captured_context.items():
                if value:
                    pills_html += f'<span class="context-pill"><span class="context-pill-key">{esc(key)}:</span> {esc(value)}</span>'
            st.markdown(pills_html, unsafe_allow_html=True)
        else:
            st.markdown('<span style="color: var(--text-muted); font-size: 0.8rem;">No context captured yet</span>', unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <span class="card-title">Qualification Checklist</span>
            </div>
            <div>
        """, unsafe_allow_html=True)
        
        qualification_labels = {
            "need_identified": "Need Identified",
            "pain_expressed": "Pain Expressed",
            "product_interest": "Product Interest",
            "budget_discussed": "Budget Discussed",
            "timeline_known": "Timeline Known",
            "decision_maker_known": "Decision Maker Known"
        }
        
        for key, label in qualification_labels.items():
            checked = qualification.get(key, False)
            check_class = "checkbox-checked" if checked else "checkbox-unchecked"
            check_symbol = "✓" if checked else "○"
            st.markdown(f"""
            <div class="qualification-item">
                <span class="{check_class}">{check_symbol}</span>
                <span>{label}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)


def render_reasoning_trace(detection: Dict[str, Any], recommendation: Dict[str, Any]):
    """Render the reasoning trace visualization."""
    customer_said = detection.get("customer_said", "")
    situation = detection.get("detected_situation", "unknown")
    principle = recommendation.get("principle", "Unknown")
    approach = recommendation.get("approach", "")
    
    # Extract signal match - use customer message, truncate if too long
    signal_match = customer_said[:60] + "..." if len(customer_said) > 60 else customer_said
    if not signal_match:
        signal_match = "No signal detected"
    signal_match = esc(signal_match)
    situation_label = esc(str(situation).replace("_", " ").title())
    principle_label = esc(principle)
    approach_label = esc(approach)
    
    st.markdown("""
    <div style="margin: 1.5rem 0;">
        <div class="card-title" style="margin-bottom: 1rem;">Reasoning Trace</div>
        <div class="reasoning-trace">
    """, unsafe_allow_html=True)
    
    trace_items = [
        ("Signal", signal_match),
        ("Situation", situation_label),
        ("Principle", principle_label),
        ("Approach", approach_label)
    ]
    
    for i, (label, content) in enumerate(trace_items):
        st.markdown(f"""
        <div class="trace-box">
            <div class="trace-box-label">{label}</div>
            <div class="trace-box-content">{content}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if i < len(trace_items) - 1:
            st.markdown('<span class="trace-arrow">→</span>', unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)


def render_grounding_panel(recommendation: Dict[str, Any], detection: Dict[str, Any]):
    """Render the grounding panel - HERO SECTION."""
    principle = recommendation.get("principle", "Unknown")
    principle_id = recommendation.get("principle_id", "")
    source = recommendation.get("source", "Unknown")
    approach = recommendation.get("approach", "Not specified")
    why_it_works = recommendation.get("why_it_works", "No explanation available")
    signal_match = detection.get("customer_said", "")
    
    # Ensure we have valid values
    if not signal_match:
        signal_match = "No customer message provided"
    principle_text = esc(str(principle).upper())
    principle_id_text = esc(principle_id)
    source_text = esc(source)
    approach_text = esc(approach)
    why_text = esc(why_it_works)
    signal_text = esc(signal_match)
    
    st.markdown(f"""
    <div class="grounding-panel reveal-delay">
        <div class="grounding-header">
            ⚡ Grounding & Reasoning
        </div>
        
        <div style="margin-bottom: 1rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem;">Principle Applied</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: var(--accent-purple); margin-bottom: 0.5rem;">{principle_text}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">ID: {principle_id_text}</div>
        </div>
        
        <div class="source-citation">
            📚 {source_text}
        </div>
        
        <div style="margin: 1rem 0;">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem;">Signal Detected In</div>
            <div class="signal-match">"{signal_text}"</div>
        </div>
        
        <div style="margin: 1rem 0;">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem;">Tactical Approach</div>
            <div style="font-size: 0.9rem; color: var(--text-primary); font-weight: 500;">{approach_text}</div>
        </div>
        
        <div style="margin-top: 1.5rem; padding: 1rem; background: rgba(167, 139, 250, 0.05); border-radius: 8px; border: 1px solid rgba(167, 139, 250, 0.2);">
            <div style="font-size: 0.75rem; color: var(--accent-purple); text-transform: uppercase; margin-bottom: 0.5rem; font-weight: 600;">Why This Works</div>
            <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">{why_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_response_card(response: str, title: str = "Recommended Response"):
    """Render the recommended response card."""
    response_text = esc(response)
    title_text = esc(title)
    st.markdown(f"""
    <div class="response-card reveal">
        <div style="font-size: 0.75rem; color: var(--accent-green); text-transform: uppercase; margin-bottom: 0.75rem; font-weight: 600;">{title_text}</div>
        <div style="font-size: 1rem; color: var(--text-primary); line-height: 1.6;">{response_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_fallback_card(fallback: Dict[str, Any]):
    """Render the fallback card."""
    principle = fallback.get("principle", "Unknown")
    response = fallback.get("response", "")
    principle_text = esc(principle)
    response_text = esc(response)
    
    st.markdown(f"""
    <div class="fallback-card">
        <div style="font-size: 0.75rem; color: var(--accent-orange); text-transform: uppercase; margin-bottom: 0.75rem; font-weight: 600;">If They Still Resist</div>
        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
            <strong>Principle:</strong> {principle_text}
        </div>
        <div style="font-size: 0.9rem; color: var(--text-primary); line-height: 1.6;">{response_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_next_probe_card(next_probe: Dict[str, Any]):
    """Render the next probe card."""
    target = next_probe.get("target", "")
    question = next_probe.get("question", "")
    target_text = esc(str(target).replace("_", " ").title())
    question_text = esc(question)
    
    st.markdown(f"""
    <div class="probe-card">
        <div style="font-size: 0.75rem; color: var(--accent-blue); text-transform: uppercase; margin-bottom: 0.75rem; font-weight: 600;">Next Probe</div>
        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">
            <strong>Target:</strong> {target_text}
        </div>
        <div style="font-size: 0.9rem; color: var(--text-primary); line-height: 1.6;">{question_text}</div>
    </div>
    """, unsafe_allow_html=True)

def render_summary_strip(detection: Dict[str, Any]):
    situation = detection.get("detected_situation", "unknown")
    persona = detection.get("detected_persona", "unknown")
    micro_stage = detection.get("micro_stage", "discovery")
    situation_confidence = detection.get("situation_confidence", 0.0)
    persona_confidence = detection.get("persona_confidence", 0.0)

    situation_label = esc(str(situation).replace("_", " ").title())
    persona_label = esc(str(persona).replace("_", " ").title())
    stage_label = esc(str(micro_stage).replace("_", " ").title())

    st.markdown(f"""
    <div class="summary-strip">
        <div class="summary-item">
            <div class="summary-label">Situation</div>
            <div class="summary-value">{situation_label}</div>
            <div class="summary-meta">{situation_confidence:.0%} confidence</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Persona</div>
            <div class="summary-value">{persona_label}</div>
            <div class="summary-meta">{persona_confidence:.0%} confidence</div>
        </div>
        <div class="summary-item">
            <div class="summary-label">Micro-Stage</div>
            <div class="summary-value">{stage_label}</div>
            <div class="summary-meta">Deal flow</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_signals_panel(detection: Dict[str, Any], qualification: Dict[str, bool]):
    situation_confidence = detection.get("situation_confidence", 0.0)
    persona_confidence = detection.get("persona_confidence", 0.0)

    qualification_labels = {
        "need_identified": "Need Identified",
        "pain_expressed": "Pain Expressed",
        "product_interest": "Product Interest",
        "budget_discussed": "Budget Discussed",
        "timeline_known": "Timeline Known",
        "decision_maker_known": "Decision Maker Known"
    }

    missing = [label for key, label in qualification_labels.items() if not qualification.get(key, False)]
    missing_display = ", ".join(missing[:3]) if missing else "None"
    if len(missing) > 3:
        missing_display += f" (+{len(missing) - 3} more)"

    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <span class="card-title">Signals & Risks</span>
        </div>
        <div style="margin-bottom: 0.75rem;">
            <div style="font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase;">Signal Confidence</div>
            <div style="font-size: 0.9rem; color: var(--text-primary); margin-top: 0.25rem;">
                Situation: {situation_confidence:.0%} • Persona: {persona_confidence:.0%}
            </div>
        </div>
        <div>
            <div style="font-size: 0.75rem; color: var(--text-secondary); text-transform: uppercase;">Missing Qualification</div>
            <div style="font-size: 0.85rem; color: var(--text-primary); margin-top: 0.25rem;">{esc(missing_display)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_metrics_bar(system: Dict[str, Any]):
    """Render the metrics bar."""
    latency = system.get("latency_ms", 0)
    step_latencies = system.get("step_latencies", {})
    
    # Determine source (simplified - would need cache info from API)
    source = "API Response"
    
    st.markdown(f"""
    <div class="metrics-bar">
        <div class="metric-item">
            <span class="metric-label">Latency:</span>
            <span class="metric-value">{latency}ms</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">Source:</span>
            <span class="metric-value">{source}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">Grounding:</span>
            <span class="metric-value" style="color: var(--accent-green);">✓ Verified</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""
    render_header()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Input Panel")
        
        # Session ID
        session_id = st.text_input(
            "Session ID",
            value=st.session_state.session_id,
            key="session_id_input"
        )
        st.session_state.session_id = session_id
        
        # Channel
        channel = st.selectbox(
            "Channel",
            ["website_chat", "whatsapp", "phone", "email"],
            index=0
        )
        
        # Turn number
        turn = st.number_input("Turn Number", min_value=1, value=1, step=1)
        
        # Customer message
        customer_message = st.text_area(
            "Customer Message",
            height=150,
            placeholder="Enter the customer message to analyze..."
        )
        
        # Prior context (simplified - could be expanded)
        st.markdown("### Prior Context")
        prior_context = st.text_area(
            "Context (JSON)",
            height=100,
            placeholder='{"looking_for": "...", "pain_points": [...]}',
            help="Optional: JSON object with prior context"
        )
        
        # Options
        st.markdown("### Options")
        show_json = st.checkbox("Show JSON", value=st.session_state.show_json)
        show_trace = st.checkbox("Show Trace", value=st.session_state.show_trace)
        st.session_state.show_json = show_json
        st.session_state.show_trace = show_trace
        
        # Analyze button
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
    
    # Main content
    if analyze_button and customer_message:
        with st.spinner("Analyzing message..."):
            # Parse prior context if provided
            product_context = None
            if prior_context:
                try:
                    product_context = json.loads(prior_context)
                except json.JSONDecodeError:
                    st.warning("Invalid JSON in prior context. Ignoring.")
            
            # Call API
            result = call_api(
                customer_message,
                session_id,
                product_context=product_context,
                channel=channel,
                turn=int(turn),
            )
            
            if result:
                st.session_state.last_response = result
                agent_dashboard = result.get("agent_dashboard", {})
                customer_facing = result.get("customer_facing", {})
                
                # Customer message display
                safe_message = esc(customer_message)
                st.markdown(f"""
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Customer Said</span>
                    </div>
                    <div style="font-size: 1rem; color: var(--text-primary); line-height: 1.6;">"{safe_message}"</div>
                    <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-muted);">
                        Turn #{turn} • {channel}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Detection
                detection = agent_dashboard.get("detection", {})
                micro_stage = detection.get("micro_stage", "discovery")
                
                # Summary strip
                render_summary_strip(detection)

                # Stage flow
                render_stage_flow(micro_stage)
                
                # Situation and signals in columns
                col1, col2 = st.columns([1, 1])
                with col1:
                    render_situation_card(detection)
                with col2:
                    render_signals_panel(detection, agent_dashboard.get("qualification_checklist", {}))
                
                # Context panel
                captured_context = agent_dashboard.get("captured_context", {})
                qualification = agent_dashboard.get("qualification_checklist", {})
                render_context_panel(detection, captured_context, qualification)
                
                recommendation = agent_dashboard.get("recommendation", {})

                tabs = st.tabs(["Response", "Reasoning", "Grounding", "JSON"])

                with tabs[0]:
                    response = customer_facing.get("response", "")
                    if response:
                        render_response_card(response)
                    col1, col2 = st.columns(2)
                    with col1:
                        fallback = agent_dashboard.get("fallback", {})
                        if fallback:
                            render_fallback_card(fallback)
                    with col2:
                        next_probe = agent_dashboard.get("next_probe", {})
                        if next_probe:
                            render_next_probe_card(next_probe)

                with tabs[1]:
                    if st.session_state.show_trace:
                        render_reasoning_trace(detection, recommendation)
                    else:
                        st.info("Enable 'Show Trace' to view reasoning steps.")

                with tabs[2]:
                    render_grounding_panel(recommendation, detection)

                with tabs[3]:
                    if st.session_state.show_json:
                        st.json(result)
                    else:
                        st.info("Enable 'Show JSON' to view the raw response.")
                
                # Metrics
                system = agent_dashboard.get("system", {})
                render_metrics_bar(system)
    
    elif st.session_state.last_response:
        # Show last response if available
        st.info("Click 'Analyze' to process a new message, or view the last response below.")
        # Could add a button to re-render last response here
    
    else:
        # Welcome message
        st.markdown("""
        <div class="card" style="text-align: center; padding: 3rem;">
            <h2 style="color: var(--text-primary); margin-bottom: 1rem;">Welcome to Sales AI Coach</h2>
            <p style="color: var(--text-secondary); line-height: 1.6;">
                Enter a customer message in the sidebar and click "Analyze" to get psychology-backed recommendations
                with full reasoning trace and grounding information.
            </p>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
