"""
MacroManager — Notebook-aesthetic Streamlit frontend
PMOS (prev. PCOS)-focused nutrition tracking interface.
Connects to FastAPI backend at API_URL (default: http://localhost:8000).
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
import base64
import time
import math
from datetime import datetime
from app.core.logger import logger

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
API_URL   = "http://localhost:8000"
RING_R    = 40
RING_CIRC = 2 * math.pi * RING_R

PALETTE = {
    "protein": {"fill": "#7F77DD", "track": "#E1DEFC", "dark": "#3C3489", "mid": "#534AB7"},
    "carbs":   {"fill": "#EF9F27", "track": "#FCE8BE", "dark": "#633806", "mid": "#854F0B"},
    "fat":     {"fill": "#1D9E75", "track": "#B5EDD8", "dark": "#085041", "mid": "#0F6E56"},
}

_DIV = '<hr style="border:none;border-top:1px solid rgba(42,31,16,0.12);margin:8px 0;"/>'

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MacroManager",
    page_icon="📓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400;1,700&display=swap');

/* ── Notebook paper background ── */
[data-testid="stAppViewContainer"] {
    background-color: #F8FAFB;
    background-image: 
        linear-gradient(to right, rgba(100, 116, 139, 0.06) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(100, 116, 139, 0.06) 1px, transparent 1px);
    background-size: 26px 26px;
}
[data-testid="stHeader"]  { background: transparent !important; }
[data-testid="stSidebar"] { display: none !important; }

/* ── Main column: clean layout ── */
.block-container {
    max-width:  460px !important;
    padding:    1.5rem 1.5rem 3rem 1.5rem !important;
    border-left: none !important;
    background:  transparent !important;
}

/* ── Base font ── */
* { font-family: 'Courier Prime', monospace !important; }
h1, h2, h3 { color: #2a1f10 !important; }

/* Force dark text for notebook aesthetic, overriding dark mode */
.stMarkdown p, .stMarkdown span, .stMarkdown div, 
[data-testid="stAppViewContainer"] .stMarkdown p, 
[data-testid="stAppViewContainer"] .stMarkdown span {
    color: #2a1f10 !important;
}

/* ── Restore Streamlit Icons ── */
[data-testid="stIcon"],
[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"],
[class*="MaterialSymbols"],
[class*="material-icons"] {
    font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
}

/* ── Text inputs ── */
.stTextInput  > div > div > input,
.stTextArea   > div > div > textarea,
.stNumberInput > div > div > input {
    background:    rgba(255, 255, 255, 0.88) !important;
    border:        1px solid rgba(42, 31, 16, 0.26) !important;
    font-size:     16px !important;
    color:         #2a1f10 !important;
    border-radius: 4px !important;
    caret-color:   #7F77DD;
}
textarea::placeholder, input::placeholder {
    font-size: 13px !important;
    color: #9a8d7c !important;
    opacity: 1 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea  > div > div > textarea:focus {
    border-color: rgba(127, 119, 221, 0.5) !important;
    box-shadow:   none !important;
    outline:      none !important;
}
.stTextInput label, .stTextArea label,
.stNumberInput label, .stSelectbox label {
    font-size: 14px !important;
    color:     #7a6d5a !important;
}

/* ── Select ── */
[data-baseweb="select"] > div {
    background:   rgba(255, 255, 255, 0.88) !important;
    border-color: rgba(42, 31, 16, 0.26) !important;
    font-size:    16px !important;
    color:        #2a1f10 !important;
}

/* ── Buttons ── */
.stButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stButton"] > button {
    background:      #EDEFF1 !important;
    border:          1.5px solid rgba(42, 31, 16, 0.30) !important;
    font-size:       16px !important;
    color:           #2a1f10 !important;
    border-radius:   4px !important;
    transition:      background 0.14s;
    height:          44px !important;
    min-height:      44px !important;
    padding:         0 !important;
    display:         flex !important;
    align-items:     center !important;
    justify-content: center !important;
    text-align:      center !important;
    width:           100% !important;
    box-sizing:      border-box !important;
}
.stButton > button div,
[data-testid="stBaseButton-secondary"] div,
[data-testid="stButton"] > button div {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
}
.stButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover   { background: #E2E6E9 !important; }
.stButton > button:active,
[data-testid="stBaseButton-secondary"]:active  { background: #D7DBDF !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background:    transparent !important;
    border-bottom: 1px solid rgba(42, 31, 16, 0.14) !important;
    gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    font-size:   15px !important;
    color:       #9a8d7c !important;
    background:  transparent !important;
    padding:     6px 14px !important;
}
.stTabs [aria-selected="true"] {
    color:         #2a1f10 !important;
    background:    transparent !important;
}
div[data-baseweb="tab-highlight"],
[data-testid="stTabsSelectionIndicator"] {
    background-color: #8a8a8a !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 12px !important; }

/* ── Expanders ── */
[data-testid="stExpander"] {
    border:        1px solid rgba(42, 31, 16, 0.13) !important;
    background:    rgba(255, 255, 255, 0.65) !important;
    border-radius: 4px !important;
    margin-bottom: 6px !important;
}
[data-testid="stExpander"] div[role="button"] p,
[data-testid="stExpander"] details summary p,
[data-testid="stExpanderToggleIcon"] { color: #2a1f10 !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: #7F77DD !important; }

/* ── Alerts ── */
.stAlert { border-radius: 4px !important; }

/* ── Camera ── */
[data-testid="stCameraInput"] label { font-size: 15px !important; color: #7a6d5a !important; }

/* ── Journal Containment ── */
div[style*="overflow-y: auto"] {
    background: #FFFFFF !important;
    border: 1px solid rgba(42, 31, 16, 0.15) !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
    padding: 16px !important;
    color: #2a1f10 !important;
}

.journal-section-box {
    background: rgba(255, 255, 255, 0.5) !important;
    border: 1px solid rgba(42, 31, 16, 0.2) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    margin-bottom: 20px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
}

.nowrap { white-space: nowrap !important; }
.wrap { 
    white-space: normal !important; 
    word-break: break-word !important; 
}

.nowrap { white-space: nowrap !important; }
.wrap { 
    white-space: normal !important; 
    word-break: break-word !important; 
}

/* ── Journal Table Fixes ── */
div[data-testid="stHorizontalBlock"]:has(div .journal-row-item) {
    display: flex !important;
    flex-wrap: nowrap !important;
    gap: 2px !important;
    width: 100% !important;
}
div[data-testid="stHorizontalBlock"]:has(div .journal-row-item) > div {
    min-width: 0 !important;
    flex-shrink: 1 !important;
}
.journal-row-item {
    font-size: 12px !important;
}
div[data-testid="stHorizontalBlock"]:has(div .journal-row-item) > div {
    min-width: 0 !important; /* Allow columns to shrink below their default min-width */
}

/* ── Square Journal Buttons ── */
div[data-testid="stHorizontalBlock"]:has(div .journal-row-item) [data-testid="stButton"] {
    width: 25px !important;
    display: flex !important;
    justify-content: center !important;
}
div[data-testid="stHorizontalBlock"]:has(div .journal-row-item) button {
    width: 25px !important;
    min-width: 25px !important;
    max-width: 25px !important;
    height: 25px !important;
    min-height: 25px !important;
    padding: 0 !important;
    font-size: 12px !important;
    border-radius: 4px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* Clean borders for containers */
.stContainer {
    border: 1px solid rgba(42, 31, 16, 0.15) !important;
    border-radius: 8px !important;
    padding: 12px !important;
}

/* Hide Streamlit chrome */
#MainMenu, footer, .stDeployButton,
[data-testid="stToolbar"] { display: none !important; }

/* Loading animations */
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.spin { animation: spin 2s linear infinite !important; }
.pulse { animation: pulse 1.5s ease-in-out infinite !important; }

/* ── Full-Screen Loader Styles ── */
.loader-container {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(248, 250, 251, 0.6);
    backdrop-filter: blur(4px);
    z-index: 9999;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
    text-align: center;
}
.loader-card {
    background: white;
    border: 1px solid rgba(42, 31, 16, 0.15);
    border-radius: 16px;
    padding: 32px 24px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
    max-width: 320px;
    width: 100%;
}
.notebook-spinner {
    width: 60px;
    height: 60px;
    border: 3px solid #EDEFF1;
    border-top: 3px solid #7F77DD;
    border-radius: 50%;
    margin: 0 auto 20px;
    animation: spin 1s linear infinite;
    display: flex;
    justify-content: center;
    align-items: center;
}
.loader-icon {
    font-size: 20px;
    animation: pulse 1.5s ease-in-out infinite;
}
.loader-title {
    font-weight: bold;
    font-size: 18px;
    color: #2a1f10;
    margin-bottom: 8px;
}
.loader-message {
    font-size: 14px;
    color: #7a6d5a;
    line-height: 1.4;
}

/* Premium Loading Overlay */
.loader-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 70vh;
    text-align: center;
}
.loader-card {
    background: #FFFFFF !important;
    border: 1.5px solid rgba(42, 31, 16, 0.15) !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(42, 31, 16, 0.06) !important;
    padding: 40px 30px !important;
    max-width: 420px;
    width: 100%;
    margin: 0 auto;
}
.notebook-spinner {
    position: relative;
    width: 80px;
    height: 80px;
    margin: 0 auto 24px auto;
}
.notebook-spinner::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    border-radius: 50%;
    border: 3px solid rgba(127, 119, 221, 0.12);
}
.notebook-spinner::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    border-radius: 50%;
    border: 3px solid transparent;
    border-top-color: #7F77DD;
    animation: spin 1.2s cubic-bezier(0.5, 0.1, 0.4, 0.9) infinite;
}
.loader-icon {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 32px;
    line-height: 1;
    animation: pulse 1.5s ease-in-out infinite;
}
.loader-title {
    font-size: 18px;
    font-weight: bold;
    color: #2a1f10 !important;
    margin-bottom: 8px;
}
.loader-message {
    font-size: 14px;
    color: #7a6d5a !important;
    line-height: 1.5;
}

/* Copilot Thinking/Typing bubble */
.copilot-thinking-bubble {
    background: rgba(127, 119, 221, 0.08) !important;
    border-left: 3px solid #7F77DD !important;
    padding: 10px 14px !important;
    border-radius: 4px 12px 12px 12px !important;
    margin: 10px 0 !important;
    display: inline-flex;
    align-items: center;
    gap: 6px;
}
.dot-pulse {
    width: 6px;
    height: 6px;
    background: #7F77DD;
    border-radius: 50%;
    animation: dot-pulse 1.4s infinite ease-in-out both;
}
.dot-pulse:nth-child(1) { animation-delay: -0.32s; }
.dot-pulse:nth-child(2) { animation-delay: -0.16s; }
@keyframes dot-pulse {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1.1); opacity: 1; }
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_GOAL_DEFAULTS = {"protein": 140.0, "carbs": 200.0, "fat": 65.0, "calories": 1800.0}

def init_session():
    defaults = {
        "consumed":         {"protein": 0.0, "carbs": 0.0, "fat": 0.0,
                             "calories": 0.0, "fiber": 0.0, "sugar": 0.0},
        "goals":            SYSTEM_GOAL_DEFAULTS.copy(),
        "weekly":           {},
        "journal_grouped":  {},
        "memory_content":   "",
        "pending_meal_id":  None,
        "last_refreshed":   0.0,
        "current_page":     None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fetch_summary(date=None):
    try:
        params = {"date": date} if date else {}
        r = requests.get(f"{API_URL}/summary", params=params, timeout=6)
        r.raise_for_status()
        d = r.json()
        st.session_state.consumed        = d["daily"]["consumed"]
        st.session_state.goals           = d["daily"]["goals"]
        st.session_state.weekly          = d.get("weekly", {})
        st.session_state.journal_grouped = d["daily"].get("grouped", {})
        st.session_state.last_refreshed  = time.time()
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the backend — make sure the API is running on localhost:8000.")
    except Exception as exc:
        st.warning(f"Data fetch failed: {exc}")


def api_start_log(text, meal_type, environment="restaurant", is_voice=False):
    r = requests.post(
        f"{API_URL}/log/start",
        json={"text": text, "meal_type": meal_type, "environment": environment, "is_voice": is_voice},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["meal_id"]


def api_log_status(meal_id):
    r = requests.get(f"{API_URL}/log/status/{meal_id}", timeout=5)
    r.raise_for_status()
    return r.json().get("status", "processing")


def api_vision_log(b64, environment, hint):
    r = requests.post(
        f"{API_URL}/vision-log",
        json={"base64_image": b64, "environment": environment, "hint": hint},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def api_update_goals(p, c, f, cal):
    r = requests.post(
        f"{API_URL}/goals",
        json={"protein": p, "carbs": c, "fat": f, "calories": cal},
        timeout=5,
    )
    r.raise_for_status()


def api_onboard(bio):
    r = requests.post(f"{API_URL}/onboard", json={"bio_text": bio}, timeout=25)
    r.raise_for_status()
    return r.json()


def api_save_memory(text):
    r = requests.post(f"{API_URL}/memory", json={"text": text}, timeout=10)
    r.raise_for_status()
    return r.json().get("content", "")


def api_fetch_memory():
    r = requests.get(f"{API_URL}/memory", timeout=5)
    r.raise_for_status()
    return r.json().get("content", "")


def api_ask_copilot(query, remaining, memory_context=""):
    r = requests.post(
        f"{API_URL}/planner",
        json={"user_query": query, "remaining_macros": remaining, "memory_context": memory_context},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("suggestion", "No suggestion available.")


def api_delete_meal(meal_id):
    r = requests.delete(f"{API_URL}/meals/{meal_id}", timeout=5)
    r.raise_for_status()
    return r.json()


def api_update_meal(meal_id, items):
    r = requests.patch(
        f"{API_URL}/meals/{meal_id}",
        json={"items": items},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def api_clear_meals(date):
    r = requests.delete(f"{API_URL}/meals/clear", params={"date": date}, timeout=5)
    r.raise_for_status()
    return r.json()


def sync_get(url, params=None):
    return requests.get(url, params=params, timeout=10)



# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _section_header(text, sub=None):
    """Renders a bold 17px section heading, with an optional 13px grey sub-label."""
    sub_html = (
        f'<span style="font-family:\'Courier Prime\',monospace;font-size:13px;'
        f'color:#9a8d7c;"> ({sub})</span>' if sub else ""
    )
    st.markdown(
        f'<p style="font-family:\'Courier Prime\',monospace;font-weight:bold;font-size:17px;'
        f'color:#2a1f10;margin:18px 0 6px;">{text}{sub_html}</p>',
        unsafe_allow_html=True,
    )


def _weekly_bar(label, consumed, goal, fill, track):
    """Renders a single horizontal weekly progress bar as an HTML string."""
    p     = min(consumed / max(goal, 1), 1.0)
    pct_w = round(p * 100, 1)
    color = "#EF9F27" if (p >= 0.88 and label == "carbs") else fill
    return (
        f'<div style="margin:5px 0;">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;'
        f'font-family:\'Courier Prime\',monospace;font-size:12px;color:#7a6d5a;margin-bottom:3px;">'
        f'<span style="font-size:15px;color:#2a1f10;">{label}</span>'
        f'<span>{int(round(consumed))}g / {int(round(goal))}g</span></div>'
        f'<div style="background:{track};border-radius:3px;height:6px;overflow:hidden;">'
        f'<div style="background:{color};width:{pct_w}%;height:100%;border-radius:3px;"></div>'
        f'</div></div>'
    )


def macro_state(consumed, goal):
    """Returns (state, clamped_pct).  state: 'normal' | 'warning' | 'complete'"""
    if goal <= 0:
        return "normal", 0.0
    pct = consumed / goal
    if pct >= 1.0:
        return "complete", 1.0
    if pct >= 0.82:
        return "warning", pct
    return "normal", pct


def arc_dash(pct):
    fill = round(min(max(pct, 0.0), 1.0) * RING_CIRC, 2)
    gap  = round(RING_CIRC - fill + 8, 2)   # +8 gap prevents visual closure
    return fill, gap


# ─────────────────────────────────────────────────────────────────────────────
# RENDER: HUD
# ─────────────────────────────────────────────────────────────────────────────
def _ring(macro, consumed, goal, cx, pct, state):
    """Build SVG group for a single progress ring."""
    pal       = PALETTE[macro]
    fill, gap = arc_dash(pct)
    sw        = 9.5 if state == "warning" else 7
    v_weight  = "700" if state == "complete" else "400"
    v_color   = pal["dark"] if state in ("complete", "warning") else "#2a1f10"
    cy        = 62

    val_str  = f"{int(round(consumed))}g"
    goal_str = f"of {int(round(goal))}g"

    out = []
    # track ring
    out.append(
        f'<circle cx="{cx}" cy="{cy}" r="{RING_R}" fill="none" '
        f'stroke="{pal["track"]}" stroke-width="7"/>'
    )
    # progress arc
    out.append(
        f'<circle cx="{cx}" cy="{cy}" r="{RING_R}" fill="none" '
        f'stroke="{pal["fill"]}" stroke-width="{sw}" '
        f'stroke-dasharray="{fill} {gap}" stroke-linecap="round" '
        f'transform="rotate(-90 {cx} {cy})"/>'
    )
    # completion: thin outer halo
    if state == "complete":
        out.append(
            f'<circle cx="{cx}" cy="{cy}" r="47" fill="none" '
            f'stroke="{pal["fill"]}" stroke-width="1.5" opacity="0.36"/>'
        )
    # warning: small dot at ~1 o'clock
    if state == "warning":
        wx = cx + int(RING_R * 0.72)
        wy = cy - int(RING_R * 0.72)
        out.append(f'<circle cx="{wx}" cy="{wy}" r="5.5" fill="{pal["fill"]}"/>')
        out.append(
            f'<text x="{wx}" y="{wy + 4}" text-anchor="middle" '
            f'font-size="8" font-weight="700" '
            f'fill="{pal["dark"]}">!</text>'
        )
    # consumed value
    out.append(
        f'<text x="{cx}" y="{cy - 6}" text-anchor="middle" '
        f'font-size="13" font-weight="{v_weight}" '
        f'fill="{v_color}">{val_str}</text>'
    )
    # macro label
    out.append(
        f'<text x="{cx}" y="{cy + 9}" text-anchor="middle" '
        f'font-size="13" fill="{pal["mid"]}">{macro}</text>'
    )
    # goal label below ring
    out.append(
        f'<text x="{cx}" y="{cy + 53}" text-anchor="middle" '
        f'font-size="10" fill="#9a8d7c">{goal_str}</text>'
    )
    return "".join(out)


def render_hud():
    c, g = st.session_state.consumed, st.session_state.goals

    p_st,  p_pct  = macro_state(c["protein"],  g["protein"])
    ca_st, ca_pct = macro_state(c["carbs"],     g["carbs"])
    f_st,  f_pct  = macro_state(c["fat"],       g["fat"])

    cal_pct    = min(c["calories"] / max(g["calories"], 1), 1.4)
    cal_val    = f'{int(round(c["calories"])):,}'
    cal_goal   = f'{int(round(g["calories"])):,}'
    cal_color  = "#085041" if cal_pct >= 1.0 else ("#633806" if cal_pct >= 0.92 else "#2a1f10")
    cal_weight = "700" if cal_pct >= 1.0 else "400"

    rings = (
        _ring("protein", c["protein"], g["protein"], 50,  p_pct,  p_st)  +
        _ring("carbs",   c["carbs"],   g["carbs"],   150, ca_pct, ca_st) +
        _ring("fat",     c["fat"],     g["fat"],     250, f_pct,  f_st)
    )

    st.markdown(f"""
<div style="margin:4px 0 14px;">
  <div style="text-align:center;margin-bottom:10px;line-height:1.1;">
    <span style="font-family:'Courier Prime',monospace;font-size:28px;
                 font-weight:{cal_weight};color:{cal_color};">{cal_val}</span>
    <span style="font-family:'Courier Prime',monospace;font-size:14px;
                 color:#9a8d7c;">&thinsp;/ {cal_goal} kcal</span>
  </div>
  <svg viewBox="0 0 300 125" width="100%" xmlns="http://www.w3.org/2000/svg"
       style="font-family:'Courier Prime',monospace;">
    {rings}
  </svg>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# RENDER: EMPATHETIC MESSAGES
# ─────────────────────────────────────────────────────────────────────────────
def render_message():
    c, g = st.session_state.consumed, st.session_state.goals

    def pct(k):
        return c[k] / max(g[k], 1)

    msgs = []

    if pct("protein") >= 1.0:
        msgs.append(("#1D9E75", "✓  Protein goal hit — muscles sorted for the day."))
    elif pct("protein") >= 0.70:
        rem = int(round(g["protein"] - c["protein"]))
        msgs.append(("#7F77DD", f"→  {rem}g of protein to go. You've got this!"))

    if pct("carbs") > 1.0:
        msgs.append(("#854F0B", "·  Carbs are over today. It happens! Let's just focus on balancing tomorrow."))
    elif pct("carbs") >= 0.85:
        msgs.append(("#EF9F27", "·  Carbs are close to the daily limit. Be mindful of the next meal."))

    if pct("calories") >= 1.0:
        msgs.append(("#633806", "·  Calorie goal reached. Your body has enough for today — time to rest."))

    if not msgs and c["calories"] < 50:
        msgs.append(("#9a8d7c", "→  Nothing logged yet — how's the day starting?"))

    for color, text in msgs[:2]:
        st.markdown(
            f'<p style="font-family:\'Courier Prime\',monospace;font-size:14px;'
            f'color:{color};margin:2px 0;line-height:1.4;">{text}</p>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# RENDER: WEEKLY BUFFER
# ─────────────────────────────────────────────────────────────────────────────
def render_weekly():
    w = st.session_state.weekly
    if not w:
        return
 
    st.markdown(_DIV, unsafe_allow_html=True)
    wg   = w.get("weekly_goals", {})
    days = w.get("days_logged", 0)
    
    # --- Insulin Guardrail Logic ---
    c, g = st.session_state.consumed, st.session_state.goals
    
    # 7-day capacity
    w_carb_max = g.get("carbs", 200.0) * 7
    w_fat_max = g.get("fat", 65.0) * 7
    
    w_carb_consumed = w.get("carbs", 0.0)
    w_fat_consumed = w.get("fat", 0.0)
    
    # Daily ceiling (130%)
    daily_carb_goal = g.get("carbs", 200.0)
    daily_fat_goal = g.get("fat", 65.0)
    today_carb = c.get("carbs", 0.0)
    today_fat = c.get("fat", 0.0)
    
    # Carb Guardrail
    carb_buffer_left = w_carb_max - w_carb_consumed
    carb_ceiling_left = (daily_carb_goal * 1.3) - today_carb
    allowable_carb = min(carb_buffer_left, carb_ceiling_left)
    
    # Fat Guardrail
    fat_buffer_left = w_fat_max - w_fat_consumed
    fat_ceiling_left = (daily_fat_goal * 1.3) - today_fat
    allowable_fat = min(fat_buffer_left, fat_ceiling_left)
    
    day_label = f"{days} day{'s' if days != 1 else ''} logged"
    inner = (
        _weekly_bar("protein", w.get("protein", 0), wg.get("protein", 1), "#7F77DD", "#E1DEFC") +
        _weekly_bar("carbs",   w.get("carbs", 0),   wg.get("carbs", 1),   "#EF9F27", "#FCE8BE") +
        _weekly_bar("fat",     w.get("fat", 0),     wg.get("fat", 1),     "#1D9E75", "#B5EDD8")
    )
    
    _section_header("this week", sub=day_label)
    st.markdown(f'<div style="margin:0 0 16px;">{inner}</div>', unsafe_allow_html=True)
    
    st.markdown('<p style="font-size:12px; color:#7a6d5a; margin-bottom:4px; font-weight:bold;">Insulin Guardrail (Allowable Today):</p>', unsafe_allow_html=True)
    if carb_ceiling_left <= 0 or fat_ceiling_left <= 0:
        st.error("🚨 130% Daily Limit Reached. Weekly buffer locked to prevent insulin spike.")
    else:
        st.info(f"Carbs: {max(0, allowable_carb):.1f}g | Fats: {max(0, allowable_fat):.1f}g")




# ─────────────────────────────────────────────────────────────────────────────
# RENDER: FOOD LOG
# ─────────────────────────────────────────────────────────────────────────────
_MIC_HTML = """<!DOCTYPE html>
<html>
<head>
<style>
  body { margin:0; padding:0; background:transparent; overflow:hidden; 
         display:flex; justify-content:center; align-items:center; height:48px; }
  #btn {
    width: 44px; height: 44px; border-radius: 50%;
    background: #EDEFF1;
    border: 1.5px solid rgba(42, 31, 16, 0.30);
    cursor: pointer; display: flex; align-items: center; justify-content: center;
    transition: all 0.2s ease;
    outline: none;
    position: relative;
  }
  #btn svg { width: 20px; height: 20px; fill: #2a1f10; transition: fill 0.2s; }
  #btn:hover { background: #E2E6E9; }
  #btn:active { background: #D7DBDF; }
  
  /* Recording State */
  #btn.recording {
    background: #FFEBEB !important;
    border-color: #C83232 !important;
    box-shadow: 0 0 0 0 rgba(200, 50, 50, 0.7);
    animation: pulse-red 1.5s infinite;
  }
  #btn.recording svg { fill: #C83232 !important; }

  @keyframes pulse-red {
    0% { box-shadow: 0 0 0 0 rgba(200, 50, 50, 0.7); }
    70% { box-shadow: 0 0 0 10px rgba(200, 50, 50, 0); }
    100% { box-shadow: 0 0 0 0 rgba(200, 50, 50, 0); }
  }
</style>
</head>
<body>
<button id="btn" onclick="toggle()" title="Tap to speak">
  <svg id="icon" viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>
</button>
<script>
var rec = null;
var isRecording = false;

function toggle() {
  var b = document.getElementById('btn');
  var i = document.getElementById('icon');

  if (isRecording) {
    if (rec) rec.stop();
    return;
  }

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    alert('Speech recognition not supported in this browser.');
    return;
  }

  rec = new SR();
  rec.lang = 'en-IN';
  rec.interimResults = false;
  rec.maxAlternatives = 1;

  rec.onstart = function() {
    isRecording = true;
    b.classList.add('recording');
    i.innerHTML = '<path d="M6 6h12v12H6z"/>'; // Square stop icon
  };

  rec.onresult = function(e) {
    var t = Array.from(e.results).map(r => r[0].transcript).join('');
    if (t.trim()) {
      try {
        var ta = window.parent.document.querySelector('div[data-testid="stTextArea"] textarea');
        if (ta) {
          var setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
          setter.call(ta, t);
          ta.dispatchEvent(new Event('input', { bubbles: true }));
        }
      } catch(err) {
        console.error('CORS block or element not found:', err);
        navigator.clipboard.writeText(t);
      }
    }
  };

  rec.onend = function() {
    isRecording = false;
    b.classList.remove('recording');
    i.innerHTML = '<path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>';
  };

  rec.onerror = function(e) {
    console.error('Speech Error:', e);
    isRecording = false;
    b.classList.remove('recording');
    i.innerHTML = '<path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>';
    if(e.error === 'not-allowed') alert('Microphone permission denied.');
  };

  rec.start();
}
</script>
</body>
</html>"""



def render_copilot():
    # Deprecated: Copilot is now integrated into the dashboard page as a modal
    pass


def render_food_log():
    st.markdown(_DIV, unsafe_allow_html=True)
    _section_header("log a meal")

    tab_text, tab_cam = st.tabs(["✏️  text", "📷  photo"])

    # ── Text / Voice ──────────────────────────────────────
    with tab_text:
        # Environment toggle (for accurate utensil volumes at home)
        env_col, meal_col = st.columns([1.5, 1.5])
        with env_col:
            environment = st.selectbox(
                "setting",
                ["home", "restaurant", "street food", "packaged"],
                key="text_env",
                label_visibility="collapsed",
            )
        with meal_col:
            meal_type = st.selectbox(
                "meal type",
                ["breakfast", "lunch", "dinner", "snack"],
                key="mt_text",
                label_visibility="collapsed",
            )
        
        st.markdown(
            '<p style="font-size:13px;color:#9a8d7c;margin:4px 0 4px;">'
            'what did you eat?</p>',
            unsafe_allow_html=True,
        )
        
        # Removed mic button due to Chrome Iframe restrictions on mobile
        # Added a tip for native Gboard mic
        user_text = st.text_area(
            "what did you eat?",
            placeholder="e.g. 2 rotis with dal…",
            height=50,
            key="log_text",
            label_visibility="collapsed",
        )
        st.markdown(
            '<p style="font-size:11px;color:#b0a8a0;margin:4px 0 12px;text-align:right;">'
            'Tip: Use your keyboard\'s 🎙️ for voice input</p>',
            unsafe_allow_html=True,
        )

        log_clicked = st.button("log it →", key="btn_log", use_container_width=True)

        if log_clicked:
            if user_text.strip():
                try:
                    with st.spinner("📝 Processing your meal…"):
                        meal_id = api_start_log(user_text.strip(), meal_type, environment)
                        st.session_state.pending_meal_id = meal_id
                    st.success("✓ Meal logged!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Couldn't start log: {exc}")
            else:
                st.warning("Describe what you ate first.")

    # ── Camera ────────────────────────────────────────────
    with tab_cam:
        env_col, hint_col = st.columns([1.5, 1.5])
        with env_col:
            env = st.selectbox(
                "setting",
                ["home", "restaurant", "street food", "packaged"],
                key="cam_env",
                label_visibility="collapsed",
            )
        with hint_col:
            hint = st.text_input(
                "hint (optional)",
                placeholder="e.g. South Indian thali",
                key="cam_hint",
                label_visibility="collapsed",
            )
        
        uploaded_file = st.file_uploader(
            "Choose an image",
            type=["jpg", "jpeg", "png"],
            label_visibility="collapsed"
        )
        if uploaded_file is not None:
            st.image(uploaded_file, use_container_width=True, caption="Selected image")
            if st.button("analyse photo →", key="btn_vision_gallery"):
                b64 = base64.b64encode(uploaded_file.read()).decode()
                st.session_state.pending_vision_log = {
                    "b64": b64,
                    "env": env,
                    "hint": hint or ""
                }
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# RENDER: JOURNAL
# ─────────────────────────────────────────────────────────────────────────────
def render_journal():
    st.markdown(_DIV, unsafe_allow_html=True)
    _section_header("food journal")
    
    # --- Filters (on same line for mobile) ---
    col_date, col_type, col_clear = st.columns([2, 1.5, 1.5])
    with col_date:
        selected_date = st.date_input("date", value=datetime.now(), key="journal_date").strftime("%Y-%m-%d")
    with col_type:
        selected_type = st.selectbox("meal type", ["All", "breakfast", "lunch", "dinner", "snack"], key="journal_type", label_visibility="collapsed")
    with col_clear:
        if st.button("Clear Day", key="btn_clear_day", help="Clear all meals for the selected date", use_container_width=True):
            try:
                api_clear_meals(selected_date)
                fetch_summary(selected_date)
                st.toast(f"Cleared meals for {selected_date}")
                st.rerun()
            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg:
                    st.error("Clear failed: API endpoint not found (404). Please restart the server.")
                else:
                    st.error(f"Clear failed: {err_msg[:100]}")
    
    try:
        params = {"date": selected_date, "meal_type": selected_type}
        response = sync_get(f"{API_URL}/meals", params=params)
        
        if response.status_code != 200:
            st.error("Could not fetch journal data.")
            return
            
        meals = response.json()
        
        if not meals:
            st.info(f"No items logged on {selected_date}.")
            return
        
        # Group by type, include "General"
        grouped = {}
        for m in meals:
            m_type = m.get("type") or "General"
            if m_type not in grouped:
                grouped[m_type] = []
            grouped[m_type].append(m)

        # --- Fixed-Height Scrollable Container (4 entries) ---
        with st.container(border=True, height=300):
            for m_type, m_list in grouped.items():
                st.markdown(f"**{m_type.capitalize()}**")
                
                # Table Header - Sticky Wrapper (Combined into single markdown call to prevent HTML breakage)
                st.markdown(f'''
                    <div style="position: sticky; top: 0; z-index: 10; background: white; padding-bottom: 10px; border-bottom: 1px solid rgba(42,31,16,0.1); display: flex; width: 100%; gap: 0px;">
                        <div style="flex: 0 0 29.17%; font-size: 12px; color: #9a8d7c; text-align: left;"><div class="wrap"><small>Name</small></div></div>
                        <div style="flex: 0 0 16.67%; font-size: 12px; color: #9a8d7c; text-align: right;"><div class="nowrap"><small>Qty</small></div></div>
                        <div style="flex: 0 0 12.5%; font-size: 12px; color: #9a8d7c; text-align: right;"><div class="nowrap"><small>P</small></div></div>
                        <div style="flex: 0 0 12.5%; font-size: 12px; color: #9a8d7c; text-align: right;"><div class="nowrap"><small>C</small></div></div>
                        <div style="flex: 0 0 12.5%; font-size: 12px; color: #9a8d7c; text-align: right; padding-right: 8px;"><div class="nowrap"><small>F</small></div></div>
                        <div style="flex: 0 0 8.33%;"></div>
                        <div style="flex: 0 0 8.33%;"></div>
                    </div>
                ''', unsafe_allow_html=True)
                
                for m in m_list:
                    items = m['items']
                    for i, item in enumerate(items):
                        # State Check for Inline Edit
                        is_editing = (st.session_state.get("editing_meal") and 
                                      st.session_state.editing_meal["id"] == m['id'] and 
                                      st.session_state.editing_meal["index"] == i)
                        
                        # Rounding Logic
                        p_val = int(math.floor(item['macros'].get('protein', 0)))
                        c_val = int(math.ceil(item['macros'].get('carbs', 0)))
                        f_val = int(math.ceil(item['macros'].get('fat', 0)))
                        g_val = int(round(item['grams']))
                        
                        # Row for each item
                        r_col1, r_col2, r_col3, r_col4, r_col5, r_col6, r_col7 = st.columns([0.35, 0.2, 0.15, 0.15, 0.15, 0.1, 0.1])
                        with r_col1: st.markdown(f'<div class="wrap journal-row-item"><small>**{item["name"]}**</small></div>', unsafe_allow_html=True)
                        
                        with r_col2:
                            if is_editing:
                                # Inline Number Input
                                new_g = st.number_input("g", value=float(item['grams']), key=f"in_{m['id']}_{i}", label_visibility="collapsed")
                            else:
                                st.markdown(f'<div class="nowrap journal-row-item" style="text-align: right;"><small>{g_val}g</small></div>', unsafe_allow_html=True)
                                
                        with r_col3: st.markdown(f'<div class="nowrap journal-row-item" style="text-align: right;"><small>{p_val}</small></div>', unsafe_allow_html=True)
                        with r_col4: st.markdown(f'<div class="nowrap journal-row-item" style="text-align: right;"><small>{c_val}</small></div>', unsafe_allow_html=True)
                        with r_col5: st.markdown(f'<div class="nowrap journal-row-item" style="text-align: right; padding-right: 8px;"><small>{f_val}</small></div>', unsafe_allow_html=True)
                        
                        with r_col6: 
                            if is_editing:
                                # Save Action
                                if st.button("✓", key=f"save_{m['id']}_{i}", help="Save changes"):
                                    # Recalculate based on the input value
                                    ratio = new_g / item['grams'] if item.get('grams', 0) > 0 else 1
                                    
                                    # 1. Construct the edited item strictly
                                    old_macros = item.get('macros') if isinstance(item.get('macros'), dict) else {}
                                    old_sub = item.get('sub_macros') if isinstance(item.get('sub_macros'), dict) else {}
                                    
                                    new_item = {
                                        "name": str(item.get("name", "Unknown")),
                                        "grams": float(new_g),
                                        "cals": float(item.get("cals", 0) * ratio),
                                        "macros": {
                                            "protein": float(old_macros.get("protein", 0) * ratio),
                                            "carbs": float(old_macros.get("carbs", 0) * ratio),
                                            "fat": float(old_macros.get("fat", 0) * ratio),
                                        },
                                        "sub_macros": {
                                            k: float(v * ratio) if isinstance(v, (int, float)) else v 
                                            for k, v in old_sub.items()
                                        } if old_sub else None,
                                        "verified": bool(item.get("verified", False))
                                    }
                                    
                                    # 2. Clean ALL items in the list to ensure they match the server schema
                                    cleaned_list = []
                                    for idx, itm in enumerate(items):
                                        if idx == i:
                                            cleaned_list.append(new_item)
                                        else:
                                            m_data = itm.get('macros') if isinstance(itm.get('macros'), dict) else {}
                                            s_data = itm.get('sub_macros') if isinstance(itm.get('sub_macros'), dict) else {}
                                            
                                            cleaned_list.append({
                                                "name": str(itm.get("name", "Unknown")),
                                                "grams": float(itm.get("grams", 0)),
                                                "cals": float(itm.get("cals", 0)),
                                                "macros": {
                                                    "protein": float(m_data.get("protein", 0)),
                                                    "carbs": float(m_data.get("carbs", 0)),
                                                    "fat": float(m_data.get("fat", 0)),
                                                },
                                                "sub_macros": s_data if s_data else None,
                                                "verified": bool(itm.get("verified", False))
                                            })
                                    
                                    api_update_meal(m['id'], cleaned_list)
                                    fetch_summary(selected_date)
                                    del st.session_state.editing_meal
                                    st.rerun()
                            else:
                                # Edit Action
                                if st.button("✏️", key=f"edit_{m['id']}_{i}", help="Edit item"):
                                    st.session_state.editing_meal = {"id": m['id'], "index": i, "items": items}
                                    st.rerun()

                        with r_col7: 
                            if st.button("🗑️", key=f"del_{m['id']}_{i}", help="Delete item"):
                                updated_items = items[:i] + items[i+1:]
                                if updated_items:
                                    api_update_meal(m['id'], updated_items)
                                else:
                                    api_delete_meal(m['id'])
                                fetch_summary(selected_date)
                                st.rerun()
        
        # Clear editing state if it persists across page changes or something
        if st.session_state.get("current_page") == "onboarding":
            if "editing_meal" in st.session_state:
                del st.session_state.editing_meal

    except Exception as e:
        st.error(f"Journal Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# RENDER: MEMORY
# ─────────────────────────────────────────────────────────────────────────────

def render_memory_section():
    # Deprecated: Memory is now integrated into the dashboard page as a modal
    pass

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ONBOARDING
# ─────────────────────────────────────────────────────────────────────────────




# ─────────────────────────────────────────────────────────────────────────────
# PAGE: ONBOARDING
# ─────────────────────────────────────────────────────────────────────────────
def render_onboarding_page():
    st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="'
        f'background: linear-gradient(135deg, rgba(127, 119, 221, 0.16) 0%, rgba(239, 159, 39, 0.16) 50%, rgba(29, 158, 117, 0.16) 100%);'
        f'border: 1.5px solid rgba(42, 31, 16, 0.12);'
        f'border-radius: 12px;'
        f'padding: 22px 16px;'
        f'text-align: center;'
        f'margin-bottom: 24px;'
        f'box-shadow: 0 4px 24px rgba(42, 31, 16, 0.05);'
        f'backdrop-filter: blur(12px);'
        f'">'
        f'<p style="font-family:\'Courier Prime\',monospace;font-weight:bold;font-size:28px;'
        f'color:#2a1f10;margin:0;line-height:1.1;">📓 MacroManager</p>'
        f'<p style="font-size:14px;color:#7a6d5a;margin:6px 0 0 0;font-weight:500;letter-spacing:0.3px;">'
        f'PMOS goals & calibration</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p style="font-family:\'Courier Prime\',monospace;font-weight:bold;font-size:17px;'
        'color:#2a1f10;margin:0 0 6px;">PMOS baseline calibrator</p>'
        '<p style="font-size:13px;color:#9a8d7c;margin-bottom:12px;">'
        'Describe your profile for personalised PMOS macronutrient targets.</p>',
        unsafe_allow_html=True,
    )
    bio = st.text_area(
        "tell us about yourself",
        placeholder=(
            "e.g. 26F, 58 kg, 163 cm, lightly active, "
            "managing PMOS, want to reduce insulin resistance…"
        ),
        height=95,
        key="bio_text",
        label_visibility="collapsed"
    )
    if st.button("calculate my goals →", key="btn_onboard", use_container_width=True):
        if bio.strip():
            with st.spinner("Calculating PMOS-adjusted goals…"):
                try:
                    res = api_onboard(bio.strip())
                    mx  = res.get("macros", {})
                    st.success(
                        f"Goals set — Protein {int(mx.get('protein', 0))}g · "
                        f"Carbs {int(mx.get('carbs', 0))}g · "
                        f"Fat {int(mx.get('fat', 0))}g · "
                        f"{int(mx.get('calories', 0))} kcal"
                    )
                    fetch_summary()
                    time.sleep(1.5)
                    st.session_state.current_page = "dashboard"
                    st.rerun()
                except Exception as exc:
                    st.error(f"Onboarding failed: {exc}")
        else:
            st.warning("Fill in your details first.")

    st.markdown(
        '<hr style="border:none;border-top:1px solid rgba(42,31,16,0.12);margin:24px 0;"/>'
        '<p style="font-family:\'Courier Prime\',monospace;font-weight:bold;font-size:17px;'
        'color:#2a1f10;margin:0 0 14px;">manual override</p>',
        unsafe_allow_html=True,
    )
    g = st.session_state.goals
    c1, c2 = st.columns(2)
    with c1:
        new_p   = st.number_input("Protein (g)",     value=float(g["protein"]),   min_value=0.0, step=5.0,  key="g_p")
        new_c   = st.number_input("Carbs (g)",       value=float(g["carbs"]),     min_value=0.0, step=5.0,  key="g_c")
    with c2:
        new_f   = st.number_input("Fat (g)",         value=float(g["fat"]),       min_value=0.0, step=5.0,  key="g_f")
        new_cal = st.number_input("Calories (kcal)", value=float(g["calories"]),  min_value=0.0, step=50.0, key="g_cal")
    
    if st.button("save goals →", key="btn_goals", use_container_width=True):
        try:
            api_update_goals(new_p, new_c, new_f, new_cal)
            st.success("Goals saved.")
            fetch_summary()
            time.sleep(1)
            st.session_state.current_page = "dashboard"
            st.rerun()
        except Exception as exc:
            st.error(f"Couldn't save: {exc}")




# ─────────────────────────────────────────────────────────────────────────────
# ASYNC LOG POLLING & PENDING LOADERS
# ─────────────────────────────────────────────────────────────────────────────
def render_pending_meal_log():
    """Renders a beautiful full-screen loading page while polling background meal logs."""
    mid = st.session_state.pending_meal_id
    if not mid:
        return
    
    placeholder = st.empty()
    
    status_messages = [
        "Extracting food items from your text…",
        "Looking up clinical PMOS nutrition data…",
        "Calibrating insulin response values…",
        "Writing entries into food journal…",
    ]
    
    for attempt in range(1, 16):  # Max 15 attempts (~45 seconds)
        msg_idx = (attempt - 1) % len(status_messages)
        current_msg = status_messages[msg_idx]
        
        with placeholder.container():
            st.markdown(f"""
            <div class="loader-container">
                <div class="loader-card">
                    <div class="notebook-spinner">
                        <div class="loader-icon">📓</div>
                    </div>
                    <div class="loader-title">Logging Meal</div>
                    <div class="loader-message">{current_msg}</div>
                    <div style="margin-top:20px; font-size:12px; color:#9a8d7c; font-family:'Courier Prime',monospace;">
                        Attempt {attempt} of 15
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        time.sleep(1.5)
        try:
            status = api_log_status(mid)
            if status == "completed":
                st.session_state.pending_meal_id = None
                placeholder.empty()
                fetch_summary()
                st.toast("✓ Meal logged and macros updated!")
                st.rerun()
                return
        except Exception as e:
            logger.warning(f"Status check attempt {attempt} failed: {e}")
        
        if attempt == 15:  # Final attempt
            st.session_state.pending_meal_id = None
            placeholder.empty()
            st.warning("⏱️ Processing took longer than expected. Your meal is being logged in the background.")
            st.rerun()
            return
            
    st.rerun()


def render_pending_vision_log():
    """Renders a beautiful full-screen loading page while synchronous vision logging runs."""
    log_data = st.session_state.get("pending_vision_log")
    if not log_data:
        return
    
    b64 = log_data["b64"]
    env = log_data["env"]
    hint = log_data["hint"]
    
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
        <div class="loader-container">
            <div class="loader-card">
                <div class="notebook-spinner">
                    <div class="loader-icon">📸</div>
                </div>
                <div class="loader-title">Analyzing Photo</div>
                <div class="loader-message">Our clinical vision model is analyzing your photo and estimating PMOS-calibrated macronutrients…</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    try:
        api_vision_log(b64, env, hint)
        fetch_summary()
        st.session_state.pending_vision_log = None
        placeholder.empty()
        st.toast("✓ Photo logged and macros updated!")
        st.rerun()
    except Exception as exc:
        st.session_state.pending_vision_log = None
        placeholder.empty()
        st.error(f"Vision log failed: {exc}")
        time.sleep(3.0)
        st.rerun()



# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def render_dashboard_page():
    now = datetime.now()
    st.markdown(
        f'<p style="font-family:\'Courier Prime\',monospace;font-weight:bold;font-size:24px;'
        f'color:#2a1f10;margin:0;line-height:1.1;">{now.strftime("%A").lower()}</p>'
        f'<p style="font-size:15px;color:#9a8d7c;margin:0 0 14px;">'
        f'{now.strftime("%d %B %Y")}</p>',
        unsafe_allow_html=True,
    )

    # Top section: HUD + Messages + Edit Goals
    render_hud()
    render_message()
    
    if st.button("edit goals", key="btn_goto_onboarding", help="Edit your PMOS goals", use_container_width=True):
        st.session_state.current_page = "onboarding"
        st.rerun()

    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
    
    # Middle section: Food Log + Weekly Log
    with st.container(border=True):
        render_food_log()
    
    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
    
    # Main section: Food Journal
    render_journal()
    
    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
    
    # Bottom section: Weekly Log
    render_weekly()
    
    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
    
    # Bottom section: AI Tools (Dietician + Memory)
    col_dietician, col_memory = st.columns(2)
    with col_dietician:
        if st.button("💬 dietician", key="btn_copilot_modal", use_container_width=True):
            st.session_state.copilot_modal_open = True
    with col_memory:
        if st.button("📝 remember this!", key="btn_memory_modal", use_container_width=True):
            st.session_state.memory_modal_open = True
    
    # --- Dietician Modal ---
    if st.session_state.get("copilot_modal_open", False):
        with st.container(border=True):
            st.markdown("""
            <p style="font-family:'Courier Prime',monospace;font-weight:bold;font-size:16px;
            color:#2a1f10;margin:0 0 12px;">Clinical Dietician</p>
            """, unsafe_allow_html=True)
            
            c, g = st.session_state.consumed, st.session_state.goals
            remaining = {
                "protein": max(0.0, g["protein"] - c["protein"]),
                "carbs": max(0.0, g["carbs"] - c["carbs"]),
                "fat": max(0.0, g["fat"] - c["fat"]),
                "calories": max(0.0, g["calories"] - c["calories"]),
            }
            
            # Display remaining macros
            st.markdown(
                f"<small style='color:#9a8d7c;'>Remaining: P {int(remaining['protein'])}g • "
                f"C {int(remaining['carbs'])}g • F {int(remaining['fat'])}g</small>",
                unsafe_allow_html=True
            )
            
            # Chat history
            if "copilot_chat" not in st.session_state:
                st.session_state.copilot_chat = []
            
            # Display chat messages (scrollable)
            with st.container(height=250, border=False):
                for msg in st.session_state.copilot_chat:
                    if msg["role"] == "user":
                        st.markdown(f'<div style="text-align:right;color:#2a1f10;margin:6px 0;"><strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="color:#7F77DD;margin:6px 0;"><strong>Dietician:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
                
                # Render the gorgeous pulsing bubble when Dietician is thinking
                if st.session_state.get("copilot_pending_query"):
                    st.markdown("""
                    <div class="copilot-thinking-bubble">
                        <strong style="color:#7F77DD;margin-right:6px;">Dietician is thinking ...</strong>
                        <div class="dot-pulse"></div>
                        <div class="dot-pulse"></div>
                        <div class="dot-pulse"></div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Background processor for copilot query
            if st.session_state.get("copilot_pending_query"):
                query = st.session_state.copilot_pending_query
                try:
                    memory_context = st.session_state.get("memory_content", "")
                    suggestion = api_ask_copilot(query, remaining, memory_context)
                    st.session_state.copilot_chat.append({"role": "assistant", "content": suggestion})
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    st.session_state.copilot_pending_query = None
                    st.session_state.copilot_query_modal = ""
                    st.rerun()
            
            # Input for new query
            user_query = st.text_input("Your question:", placeholder="e.g. What's a good dinner?", key="copilot_query_modal", label_visibility="collapsed")
            
            col_ask, col_clear, col_close = st.columns([2, 1, 1])
            with col_ask:
                if st.button("Ask →", key="btn_ask_copilot", use_container_width=True):
                    if user_query.strip():
                        st.session_state.copilot_chat.append({"role": "user", "content": user_query})
                        st.session_state.copilot_pending_query = user_query
                        st.rerun()
            
            with col_clear:
                if st.button("Clear", key="btn_clear_copilot", use_container_width=True):
                    st.session_state.copilot_chat = []
                    st.rerun()
            
            with col_close:
                if st.button("Close", key="btn_close_copilot", use_container_width=True):
                    st.session_state.copilot_modal_open = False
                    st.rerun()
    
    # --- Memory Modal ---
    if st.session_state.get("memory_modal_open", False):
        with st.container(border=True):
            st.markdown("""
            <p style="font-family:'Courier Prime',monospace;font-weight:bold;font-size:16px;
            color:#2a1f10;margin:0 0 8px;">Personal Notes</p>
            <p style="font-size:12px;color:#9a8d7c;margin:0 0 12px;">Max 2000 tokens</p>
            """, unsafe_allow_html=True)
            
            if not st.session_state.memory_content:
                try:
                    st.session_state.memory_content = api_fetch_memory()
                except Exception:
                    st.session_state.memory_content = ""
            
            # Large text area for notes
            mem_text = st.text_area(
                "Your notes:",
                value=st.session_state.memory_content,
                height=200,
                key="mem_textarea",
                label_visibility="collapsed",
                placeholder="e.g. I'm lactose intolerant. Blue bowl = 200ml…"
            )
            
            # Token counter (approximate)
            token_count = len(mem_text.split())
            st.markdown(f"<small style='color:#9a8d7c;'>{token_count} tokens</small>", unsafe_allow_html=True)
            
            col_save, col_close = st.columns(2)
            with col_save:
                if st.button("Save →", key="btn_mem_save_modal", use_container_width=True):
                    if mem_text.strip():
                        with st.spinner("Saving…"):
                            try:
                                updated = api_save_memory(mem_text.strip())
                                st.session_state.memory_content = updated
                                st.success("Saved!")
                                time.sleep(0.5)
                            except Exception as e:
                                st.error(f"Error: {e}")
                    else:
                        st.warning("Add some notes first.")
            
            with col_close:
                if st.button("Close", key="btn_close_memory", use_container_width=True):
                    st.session_state.memory_modal_open = False
                    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ROUTER
# ─────────────────────────────────────────────────────────────────────────────
def main():
    inject_css()
    init_session()
    
    # Get current local date for consistency
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Check if this is a cold start (first load or after 30s)
    is_cold_start = time.time() - st.session_state.last_refreshed > 30
    
    if is_cold_start:
        # Show loading indicator while fetching summary
        with st.spinner("🔄 Loading your data…"):
            fetch_summary(today_str)
    
    # --- SMART ROUTING ---
    # If page is not explicitly set (first load), determine based on goals
    if st.session_state.current_page is None:
        if st.session_state.goals == SYSTEM_GOAL_DEFAULTS:
            st.session_state.current_page = "onboarding"
        else:
            st.session_state.current_page = "dashboard"

    # Conditional Rendering based on Session Router
    if st.session_state.current_page == "onboarding":
        render_onboarding_page()
    else:
        render_dashboard_page()
        
        # Render loading overlays on top of the dashboard if applicable
        if st.session_state.get("pending_vision_log"):
            render_pending_vision_log()
        elif st.session_state.get("pending_meal_id"):
            render_pending_meal_log()


if __name__ == "__main__":
    main()
