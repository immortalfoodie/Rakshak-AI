"""
Rakshak AI — Integration Dashboard
====================================
Streamlit app showing the full pipeline: risk scores, geospatial map,
scenario projections, ranked recommendations, and latency log.
Includes historical replay mode.
"""
import json
import time
import pathlib
import streamlit as st
from streamlit_folium import st_folium
from datetime import datetime

from pipeline import run_pipeline, run_pipeline_with_custom_data
from config import CORRIDORS, HISTORICAL
from map_builder import build_map
from charts import brent_chart, inr_chart, fuel_chart, state_bar

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Rakshak AI — Energy Supply Chain Resilience",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
.stApp { background: linear-gradient(135deg, #0a0a1a 0%, #101028 50%, #0d0d20 100%); }
.main .block-container { padding-top: 1.5rem; max-width: 1400px; }

/* Glass card */
.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    backdrop-filter: blur(12px);
    margin-bottom: 0.8rem;
}

/* Risk badge */
.risk-badge {
    display: inline-block; padding: 6px 18px; border-radius: 24px;
    font-weight: 600; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;
}
.risk-critical { background: rgba(255,68,68,0.25); color: #FF4444; border: 1px solid #FF4444; }
.risk-high     { background: rgba(255,167,38,0.25); color: #FFA726; border: 1px solid #FFA726; }
.risk-medium   { background: rgba(255,234,167,0.25); color: #FFEAA7; border: 1px solid #FFEAA7; }
.risk-low      { background: rgba(102,187,106,0.25); color: #66BB6A; border: 1px solid #66BB6A; }

/* Score ring */
.score-ring {
    width: 110px; height: 110px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 2rem; font-weight: 700; margin: 0 auto;
}

/* Metric card */
.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}
.metric-card .label { color: #888; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; }
.metric-card .value { color: #fff; font-size: 1.5rem; font-weight: 600; margin-top: 4px; }

/* Recommendation cards */
.rec-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: transform 0.2s, border-color 0.2s;
}
.rec-card:hover { transform: translateY(-2px); border-color: rgba(78,205,196,0.4); }

/* Latency log */
.latency-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 0.85rem;
}
.latency-row .stage { color: #aaa; } .latency-row .time { color: #4ECDC4; font-weight: 600; }

/* Replay banner */
.replay-banner {
    background: linear-gradient(90deg, rgba(255,107,107,0.15), rgba(78,205,196,0.15));
    border: 1px solid rgba(255,107,107,0.3);
    border-radius: 12px;
    padding: 12px 20px;
    text-align: center;
    margin-bottom: 1rem;
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100% { opacity: 0.8; } 50% { opacity: 1; } }

/* Header */
.header-title {
    font-size: 1.8rem; font-weight: 700;
    background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.header-sub { color: #666; font-size: 0.9rem; margin-top: -8px; }

div[data-testid="stSidebar"] { background: rgba(10,10,26,0.95); }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="header-title">🛡️ Rakshak AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="header-sub">Energy Supply Chain Resilience</p>', unsafe_allow_html=True)
    st.markdown("---")

    mode = st.radio("Mode", ["📡 Live Pipeline", "🔁 Historical Replay"], index=0)

    if mode == "🔁 Historical Replay":
        event_files = list(HISTORICAL.glob("*.json"))
        event_names = {}
        for ef in event_files:
            try:
                with open(ef) as f:
                    d = json.load(f)
                    event_names[d.get("event_name", ef.stem)] = ef
            except Exception:
                pass
        if not event_names:
            st.warning("No historical events found.")
        else:
            selected_event = st.selectbox("Select Event", list(event_names.keys()))
            replay_speed = st.slider("Replay Speed", 0.5, 5.0, 2.0, 0.5, help="x faster than real delay")
            start_replay = st.button("▶️ Start Replay", use_container_width=True, type="primary")
    else:
        st.markdown("Running pipeline with current mock data.")
        start_replay = False

    st.markdown("---")
    st.markdown(
        "<div style='color:#555;font-size:0.75rem;text-align:center;'>"
        "Integration Layer v1.0<br>Built for Rakshak AI</div>",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Helper: render a single pipeline result
# ---------------------------------------------------------------------------
def render_dashboard(result, step_label=""):
    l1 = result.layer1_output
    l2 = result.layer2_output
    l3 = result.layer3_output

    corridor = l1.get("corridor", "hormuz")
    score = l1.get("score", 0)
    alert = l1.get("alert_level", "low")

    # --- Header row ---
    if step_label:
        st.markdown(f'<div class="replay-banner">🔁 Replay Step: <b>{step_label}</b></div>',
                    unsafe_allow_html=True)

    st.markdown(f'<p class="header-title">Pipeline Dashboard</p>', unsafe_allow_html=True)

    # --- Top metrics ---
    c1, c2, c3, c4 = st.columns(4)
    score_color = "#FF4444" if score >= 75 else "#FFA726" if score >= 50 else "#66BB6A"

    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Corridor Risk Score</div>
            <div class="score-ring" style="border: 4px solid {score_color}; color: {score_color};">{score}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Alert Level</div>
            <div style="margin-top:12px;"><span class="risk-badge risk-{alert}">{alert}</span></div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="label">Corridor</div>
            <div class="value">{CORRIDORS.get(corridor, {}).get('label', corridor)}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        gdp = l2.get("projections", {}).get("gdp_drag_pct", 0)
        st.markdown(f"""<div class="metric-card">
            <div class="label">GDP Drag</div>
            <div class="value" style="color:#FF6B6B;">-{gdp}%</div>
        </div>""", unsafe_allow_html=True)

    # --- Sub-scores ---
    st.markdown("#### 📊 Signal Sub-Scores")
    subs = l1.get("sub_scores", {})
    cols = st.columns(len(subs))
    for col, (k, v) in zip(cols, subs.items()):
        label = k.replace("_", " ").title()
        c = "#FF4444" if (v or 0) >= 75 else "#FFA726" if (v or 0) >= 50 else "#66BB6A"
        with col:
            st.markdown(f"""<div class="metric-card">
                <div class="label">{label}</div>
                <div class="value" style="color:{c};">{v if v is not None else '—'}</div>
            </div>""", unsafe_allow_html=True)

    # --- Map ---
    st.markdown("#### 🗺️ Geospatial View")
    recs = l3.get("recommendations", [])
    m = build_map(corridor, recs)
    st_folium(m, use_container_width=True, height=420, returned_objects=[])

    # --- Charts ---
    st.markdown("#### 📈 Scenario Projections (Layer 2)")
    proj = l2.get("projections", {})
    ch1, ch2 = st.columns(2)
    with ch1:
        st.plotly_chart(brent_chart(proj), use_container_width=True)
    with ch2:
        st.plotly_chart(inr_chart(proj), use_container_width=True)
    ch3, ch4 = st.columns(2)
    with ch3:
        st.plotly_chart(fuel_chart(proj), use_container_width=True)
    with ch4:
        st.plotly_chart(state_bar(proj), use_container_width=True)

    # --- Recommendations ---
    st.markdown("#### 🎯 Procurement Recommendations (Layer 3)")
    for rec in recs:
        rank = rec["rank"]
        medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"#{rank}"
        cost_c = "#66BB6A" if rec["cost_delta_vs_baseline_pct"] < 5 else "#FFA726" if rec["cost_delta_vs_baseline_pct"] < 8 else "#FF4444"
        st.markdown(f"""<div class="rec-card">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:1.3rem;">{medal}</span>
                    <b style="color:#fff;font-size:1.05rem;margin-left:8px;">{rec['source_supplier']}</b>
                </div>
                <span style="color:{cost_c};font-weight:600;font-size:0.95rem;">
                    +{rec['cost_delta_vs_baseline_pct']}% vs baseline
                </span>
            </div>
            <div style="color:#aaa;font-size:0.82rem;margin-top:6px;">
                <b>Route:</b> {rec['route']} &nbsp;|&nbsp;
                <b>Tanker:</b> {rec['tanker_class']} ({rec['tanker_availability']}) &nbsp;|&nbsp;
                <b>Spot:</b> ${rec['spot_price_usd_per_bbl']}/bbl &nbsp;|&nbsp;
                <b>Lead:</b> {rec['time_to_execute_hours']}h &nbsp;|&nbsp;
                <b>Congestion:</b> {rec['port_congestion_factor']}
            </div>
            <div style="color:#999;font-size:0.8rem;margin-top:6px;font-style:italic;">
                {rec['rationale']}
            </div>
        </div>""", unsafe_allow_html=True)

    # --- Latency log ---
    st.markdown("#### ⏱️ Pipeline Latency Log")
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    for stage, ts in result.timestamps.items():
        label = stage.replace("_", " ").title()
        val = f"{ts}" if isinstance(ts, str) else f"{ts} ms"
        st.markdown(f"""<div class="latency-row">
            <span class="stage">{label}</span>
            <span class="time">{val}</span>
        </div>""", unsafe_allow_html=True)
    for stage, ms in result.latencies.items():
        label = stage.replace("_", " ").title()
        st.markdown(f"""<div class="latency-row">
            <span class="stage">{label}</span>
            <span class="time">{ms} ms</span>
        </div>""", unsafe_allow_html=True)
    total_ms = round(result.total_elapsed * 1000, 2)
    st.markdown(f"""<div class="latency-row" style="border-top:2px solid rgba(78,205,196,0.3);margin-top:4px;padding-top:10px;">
        <span class="stage" style="color:#fff;font-weight:600;">Total Elapsed</span>
        <span class="time" style="font-size:1rem;">{total_ms} ms</span>
    </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Evidence ---
    with st.expander("📋 Evidence (Layer 1)", expanded=False):
        for ev in l1.get("evidence", []):
            st.markdown(f"- **[{ev['source']}]** {ev['summary']}  \n  _{ev['timestamp']}_")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if mode == "📡 Live Pipeline":
    with st.spinner("Running pipeline…"):
        result = run_pipeline()
    render_dashboard(result)

elif mode == "🔁 Historical Replay" and start_replay:
    with open(event_names[selected_event]) as f:
        event = json.load(f)

    st.markdown(f"""<div class="replay-banner">
        🔁 <b>Replaying: {event.get('event_name', 'Unknown')}</b><br>
        <span style="font-size:0.8rem;color:#aaa;">{event.get('description', '')}</span>
    </div>""", unsafe_allow_html=True)

    placeholder = st.empty()
    steps = event.get("steps", [])
    for i, step in enumerate(steps):
        with placeholder.container():
            result = run_pipeline_with_custom_data(
                layer1=step["layer1"],
                layer2=step["layer2"],
                layer3=step["layer3"],
            )
            render_dashboard(result, step_label=f"Step {step['step']} of {len(steps)} — {event.get('event_name','')}")
        delay = step.get("delay_seconds", 3) / replay_speed
        if i < len(steps) - 1:
            time.sleep(delay)

    st.success("✅ Replay complete!")

elif mode == "🔁 Historical Replay":
    st.info("Select an event and click **Start Replay** in the sidebar.")
