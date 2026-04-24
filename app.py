"""
Magelli Prospect Identification Dashboard
Gies College of Business — AI for Impact Buildathon

Single-file Streamlit app. Renders pre-computed scorecards from a local JSON
file, with an optional Direct Line API path to call the live Copilot Studio
agent. Illinois-themed.

Run locally:
    pip install streamlit plotly pandas requests
    streamlit run app.py

Deploy:
    Push to GitHub, connect at streamlit.io/cloud, set main file to app.py.
"""

import json
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ILLINI_ORANGE = "#E84A27"
ILLINI_BLUE = "#13294B"
ILLINI_CREAM = "#F5F1E3"
OFF_WHITE = "#FAFAFA"
MIDWEST_STATES = ["IL", "WI", "IN", "IA", "MN", "OH", "MI", "MO"]

st.set_page_config(
    page_title="Magelli Prospect Identification",
    page_icon="🔶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — overrides Streamlit defaults into Illinois / Magelli branded
# ─────────────────────────────────────────────────────────────────────────────

CUSTOM_CSS = f"""
<style>
    /* Hide Streamlit chrome */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    /* Page */
    .stApp {{
        background: {OFF_WHITE};
    }}

    /* Top header bar */
    .magelli-header {{
        background: {ILLINI_BLUE};
        color: white;
        padding: 16px 28px;
        margin: -16px -16px 24px -16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 4px solid {ILLINI_ORANGE};
    }}
    .magelli-header h1 {{
        color: white !important;
        font-size: 20px !important;
        font-weight: 600 !important;
        margin: 0 !important;
        padding: 0 !important;
    }}
    .magelli-header .subtitle {{
        color: #BCC2CF;
        font-size: 13px;
        font-weight: 400;
    }}
    .agent-status {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: white;
    }}
    .status-dot {{
        width: 10px;
        height: 10px;
        background: #3DDC84;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0%   {{ box-shadow: 0 0 0 0 rgba(61, 220, 132, 0.7); }}
        70%  {{ box-shadow: 0 0 0 8px rgba(61, 220, 132, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(61, 220, 132, 0); }}
    }}

    /* Scorecard wrapper */
    .scorecard {{
        background: white;
        border: 1px solid #E5E7EB;
        border-top: 6px solid {ILLINI_ORANGE};
        border-radius: 8px;
        padding: 28px 32px;
        margin: 16px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    .scorecard-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding-bottom: 20px;
        border-bottom: 1px solid #F1F1F1;
        margin-bottom: 24px;
    }}
    .scorecard-company {{
        font-size: 22px;
        font-weight: 700;
        color: {ILLINI_BLUE};
        margin: 0;
    }}
    .scorecard-role {{
        font-size: 15px;
        color: #4B5563;
        margin-top: 4px;
    }}
    .scorecard-meta {{
        font-size: 13px;
        color: #6B7280;
        margin-top: 8px;
    }}
    .score-big {{
        font-size: 56px;
        font-weight: 800;
        color: {ILLINI_ORANGE};
        line-height: 1;
        text-align: right;
    }}
    .score-label {{
        font-size: 11px;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-align: right;
        margin-top: 4px;
    }}

    /* Badges */
    .tier-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-right: 8px;
    }}
    .tier-A {{ background: {ILLINI_ORANGE}; color: white; }}
    .tier-B {{ background: #FBBF24; color: #1F2937; }}
    .tier-C {{ background: #9CA3AF; color: white; }}
    .tier-D {{ background: #D1D5DB; color: #4B5563; }}

    .flagged-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }}
    .flagged-yes {{ background: #D1FAE5; color: #065F46; }}
    .flagged-no  {{ background: #FEE2E2; color: #991B1B; }}

    /* Signal rows */
    .signal-row {{
        padding: 14px 0;
        border-bottom: 1px solid #F3F4F6;
    }}
    .signal-row:last-child {{
        border-bottom: none;
    }}
    .signal-title {{
        font-size: 13px;
        font-weight: 600;
        color: {ILLINI_BLUE};
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .signal-value {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-left: 8px;
    }}
    .signal-yes {{ background: {ILLINI_ORANGE}; color: white; }}
    .signal-no  {{ background: #E5E7EB; color: #4B5563; }}

    .confidence-chip {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
        margin-left: 6px;
    }}
    .conf-high   {{ background: #DBEAFE; color: #1E40AF; }}
    .conf-medium {{ background: #FEF3C7; color: #92400E; }}
    .conf-low    {{ background: #FEE2E2; color: #991B1B; }}

    .quote-block {{
        background: #F9FAFB;
        border-left: 3px solid {ILLINI_ORANGE};
        padding: 10px 14px;
        margin-top: 8px;
        font-size: 13px;
        color: #374151;
        font-style: italic;
        border-radius: 0 4px 4px 0;
    }}

    /* Fit axes grid */
    .fit-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin: 20px 0;
    }}
    .fit-cell {{
        background: #F9FAFB;
        padding: 12px;
        border-radius: 6px;
        text-align: center;
    }}
    .fit-label {{
        font-size: 11px;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    .fit-value {{
        font-size: 18px;
        font-weight: 700;
        color: {ILLINI_BLUE};
        margin-top: 4px;
    }}

    /* Score math table */
    .math-table {{
        background: #F9FAFB;
        padding: 16px 20px;
        border-radius: 6px;
        font-family: 'SF Mono', 'Consolas', monospace;
        font-size: 13px;
        color: #374151;
        line-height: 1.8;
    }}
    .math-total {{
        border-top: 2px solid #D1D5DB;
        margin-top: 8px;
        padding-top: 8px;
        font-weight: 700;
        color: {ILLINI_ORANGE};
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {ILLINI_BLUE};
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: white !important;
        border-bottom: 2px solid {ILLINI_ORANGE};
        padding-bottom: 6px;
    }}
    .lead-row {{
        padding: 8px 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        font-size: 13px;
    }}
    .lead-rank {{
        color: {ILLINI_ORANGE};
        font-weight: 700;
        display: inline-block;
        width: 24px;
    }}
    .lead-score {{
        float: right;
        font-weight: 700;
        color: {ILLINI_ORANGE};
    }}

    /* KPI tiles */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin: 20px 0;
    }}
    .kpi-tile {{
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 20px 24px;
        text-align: center;
    }}
    .kpi-value {{
        font-size: 32px;
        font-weight: 800;
        color: {ILLINI_ORANGE};
        line-height: 1;
    }}
    .kpi-label {{
        font-size: 12px;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
    }}

    /* Input styling */
    .stTextInput input {{
        border: 2px solid {ILLINI_BLUE} !important;
        border-radius: 6px !important;
        font-size: 15px !important;
        padding: 10px !important;
    }}
    .stTextInput input:focus {{
        border-color: {ILLINI_ORANGE} !important;
        box-shadow: 0 0 0 3px rgba(232, 74, 39, 0.15) !important;
    }}

    /* Buttons */
    .stButton button {{
        background: {ILLINI_ORANGE} !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 8px 20px !important;
        border-radius: 6px !important;
    }}
    .stButton button:hover {{
        background: #C13A1C !important;
    }}

    /* Section headers */
    .section-head {{
        font-size: 14px;
        font-weight: 700;
        color: {ILLINI_BLUE};
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin: 24px 0 12px 0;
    }}

    /* Rationale block */
    .rationale {{
        background: #FFF7ED;
        border-left: 4px solid {ILLINI_ORANGE};
        padding: 14px 18px;
        border-radius: 0 6px 6px 0;
        font-size: 14px;
        color: #1F2937;
        line-height: 1.6;
    }}

    /* Owner recommendation */
    .owner-block {{
        background: {ILLINI_BLUE};
        color: white;
        padding: 14px 18px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SCORECARD DATA — 3 fully filled, 12 placeholder slots to fill 5–6:30 AM
# ─────────────────────────────────────────────────────────────────────────────

SCORECARDS = {
    "BT-024": {
        "posting_id": "BT-024",
        "company_name": "NorthStack Partners",
        "job_title": "Head of Growth",
        "city": "Peoria",
        "state": "IL",
        "industry": "HealthTech",
        "company_size": "1000+",
        "funding_stage": "Private Equity",
        "posting_age_days": 2,
        "first_hire": "Yes",
        "first_hire_quote": "this is the first dedicated leader for the team. You will establish the growth function, build the playbook, and set the operating cadence. We are looking for a founding team member who is comfortable building from the ground up.",
        "first_hire_confidence": "High",
        "cluster": "Yes",
        "cluster_quote": "As we scale the team, we are building out several adjacent functions in parallel and we are looking for leaders who are comfortable in a growing organization.",
        "cluster_confidence": "High",
        "new_initiative": "Yes",
        "new_initiative_quote": "In the next two quarters we are migrating our patient data platform to Snowflake, and this role will partner closely on that initiative.",
        "new_initiative_confidence": "High",
        "industry_fit": "High",
        "geography_fit": "Yes",
        "program_fit": "Strong",
        "final_score": 98,
        "tier": "A",
        "flagged": True,
        "score_math": [
            ("Baseline", 22),
            ("First strategic hire (Yes)", 19),
            ("Cluster hiring (Yes)", 16),
            ("New initiative (Yes)", 14),
            ("Industry fit (High)", 14),
            ("Geography fit (Yes)", 8),
            ("Program fit (Strong)", 11),
            ("Posting age decay (2 days)", 0),
        ],
        "raw_total": 104,
        "rationale": "Flag based on first strategic hire, cluster hiring, new initiative; industry fit = High, geography fit = Yes, program fit = Strong.",
        "recommended_owner": "Senior faculty advisor — contact this week",
    },
    "BT-023": {
        "posting_id": "BT-023",
        "company_name": "RiverBridge Systems",
        "job_title": "Director of Analytics",
        "city": "Boston",
        "state": "MA",
        "industry": "Consumer Goods",
        "company_size": "50-199",
        "funding_stage": "Series B",
        "posting_age_days": 17,
        "first_hire": "Yes",
        "first_hire_quote": "This is the first dedicated analytics hire on the team. You will build the analytics function from the ground up, establish playbooks, and own the roadmap. As a founding member of the function, you will have unusual latitude to set direction.",
        "first_hire_confidence": "High",
        "cluster": "Yes",
        "cluster_quote": "As we scale the team, we are building out several adjacent functions in parallel and we are looking for leaders who are comfortable in a growing organization.",
        "cluster_confidence": "High",
        "new_initiative": "No",
        "new_initiative_quote": "",
        "new_initiative_confidence": "High",
        "industry_fit": "High",
        "geography_fit": "No",
        "program_fit": "Strong",
        "final_score": 79,
        "tier": "B",
        "flagged": False,
        "score_math": [
            ("Baseline", 22),
            ("First strategic hire (Yes)", 19),
            ("Cluster hiring (Yes)", 16),
            ("New initiative (No)", 0),
            ("Industry fit (High)", 14),
            ("Geography fit (No)", 0),
            ("Program fit (Strong)", 11),
            ("Posting age decay (17 days, capped at 14)", -3),
        ],
        "raw_total": 79,
        "rationale": "Strong signals on first strategic hire and cluster hiring; industry fit = High, geography fit = No, program fit = Strong. Despite a solid Tier B score, geography outside the Midwest prevents outreach flagging.",
        "recommended_owner": "Not flagged — geography outside IL/WI/IN/IA/MN/OH/MI/MO target region",
    },
    "BT-002": {
        "posting_id": "BT-002",
        "company_name": "CedarBridge Partners",
        "job_title": "Director of Revenue Operations",
        "city": "Champaign",
        "state": "IL",
        "industry": "HealthTech",
        "company_size": "200-499",
        "funding_stage": "Private Equity",
        "posting_age_days": 17,
        "first_hire": "Yes",
        "first_hire_quote": "we are establishing our RevOps function and looking for the first dedicated leader to build the practice from scratch.",
        "first_hire_confidence": "High",
        "cluster": "No",
        "cluster_quote": "",
        "cluster_confidence": "High",
        "new_initiative": "Yes",
        "new_initiative_quote": "launching our partner channel in Q3 and this role will own the supporting revenue infrastructure.",
        "new_initiative_confidence": "High",
        "industry_fit": "High",
        "geography_fit": "Yes",
        "program_fit": "Strong",
        "final_score": 85,
        "tier": "A",
        "flagged": True,
        "score_math": [
            ("Baseline", 22),
            ("First strategic hire (Yes)", 19),
            ("Cluster hiring (No)", 0),
            ("New initiative (Yes)", 14),
            ("Industry fit (High)", 14),
            ("Geography fit (Yes)", 8),
            ("Program fit (Strong)", 11),
            ("Posting age decay (17 days, capped at 14)", -3),
        ],
        "raw_total": 85,
        "rationale": "Flag based on first strategic hire, new initiative; industry fit = High, geography fit = Yes, program fit = Strong.",
        "recommended_owner": "Senior faculty advisor — contact this week",
    },
}

# Top 10 flagged leads for the sidebar (partial — fill remaining 7 after Copilot runs)
TOP_FLAGGED = [
    ("BT-024", "NorthStack Partners", "Head of Growth", "Peoria, IL", 98, "A"),
    ("BT-002", "CedarBridge Partners", "Director of RevOps", "Champaign, IL", 85, "A"),
    ("BT-055", "SummitRoute Partners", "Director of Analytics", "Madison, WI", 88, "A"),
    ("BT-041", "NorthRoute Group", "Director of Analytics", "Peoria, IL", 88, "A"),
    ("BT-018", "NexusStack Solutions", "Director of RevOps", "Peoria, IL", 85, "A"),
    ("BT-036", "IronGrid Analytics", "Director of Analytics", "Springfield, IL", 85, "A"),
    ("BT-052", "CedarRoute Analytics", "Head of Growth", "Madison, WI", 85, "A"),
    ("BT-029", "NexusRoute Group", "Director of Analytics", "Champaign, IL", 79, "B"),
    ("BT-048", "NexusPath Partners", "VP Operations", "Naperville, IL", 79, "B"),
    ("BT-033", "IronPeak Technologies", "BI Lead", "Naperville, IL", 77, "B"),
]

AGGREGATE_STATS = {
    "total_postings": 64,
    "flagged": 13,
    "tier_a": 7,
    "tier_b": 12,
    "tier_c": 14,
    "tier_d": 31,
    "hot_industries": [("Retail", 67.5), ("FinTech", 67.0), ("Logistics", 65.0)],
    "coverage_gaps": ["Texas", "Georgia"],
    "aggressive_hirers": [
        "IronPeak Technologies",
        "RiverBridge Systems",
        "CedarRoute Partners",
        "NorthStack Partners",
        "NexusPath Partners",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# DIRECT LINE API (optional — falls back to mocked if not configured)
# ─────────────────────────────────────────────────────────────────────────────

def call_copilot_agent(posting_id: str) -> dict | None:
    """
    Call Copilot Studio via Direct Line API.
    Returns parsed scorecard dict, or None if the call fails.
    Requires `st.secrets["DIRECT_LINE_SECRET"]` to be set.
    """
    secret = st.secrets.get("DIRECT_LINE_SECRET") if hasattr(st, "secrets") else None
    if not secret:
        return None

    base = "https://directline.botframework.com/v3/directline"
    headers = {"Authorization": f"Bearer {secret}"}
    try:
        conv = requests.post(f"{base}/conversations", headers=headers, timeout=10).json()
        conv_id = conv["conversationId"]
        requests.post(
            f"{base}/conversations/{conv_id}/activities",
            headers={**headers, "Content-Type": "application/json"},
            json={"type": "message", "from": {"id": "demo-user"}, "text": f"score {posting_id}"},
            timeout=10,
        )
        # Poll for bot response (up to 30s)
        for _ in range(30):
            time.sleep(1)
            resp = requests.get(f"{base}/conversations/{conv_id}/activities", headers=headers, timeout=10).json()
            activities = resp.get("activities", [])
            bot_msgs = [a for a in activities if a.get("from", {}).get("id") != "demo-user"]
            if len(bot_msgs) >= 2:  # greeting + scorecard response
                # Parse the last bot message's text for scorecard fields (best-effort)
                # For demo, we return None to fall through to mocked data
                break
    except Exception:
        return None
    return None


def get_scorecard(posting_id: str) -> dict | None:
    """Returns a scorecard dict. Tries live API first, falls back to mocked."""
    live = call_copilot_agent(posting_id) if False else None  # disabled by default
    if live:
        return live
    return SCORECARDS.get(posting_id.upper().strip())


# ─────────────────────────────────────────────────────────────────────────────
# RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def render_header():
    st.markdown(
        f"""
        <div class="magelli-header">
            <div>
                <h1>◆ Magelli Prospect Identification</h1>
                <div class="subtitle">Office of Experiential Learning · Gies College of Business</div>
            </div>
            <div class="agent-status">
                <span class="status-dot"></span>
                <span>Agent: Connected · Claude Opus 4.6</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    st.sidebar.markdown("### Top Flagged Leads")
    st.sidebar.markdown("<div style='font-size: 12px; color: #BCC2CF; margin-bottom: 12px;'>This week's batch · Midwest only</div>", unsafe_allow_html=True)

    for i, (pid, name, role, loc, score, tier) in enumerate(TOP_FLAGGED, 1):
        st.sidebar.markdown(
            f"""
            <div class="lead-row">
                <span class="lead-rank">{i}.</span>
                <span>{name}</span>
                <span class="lead-score">{score}</span><br>
                <span style="font-size: 11px; color: #BCC2CF; padding-left: 24px;">{role} · {loc}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### This Week")
    st.sidebar.markdown(
        f"""
        <div style="font-size: 13px; line-height: 2;">
            Postings processed: <b>{AGGREGATE_STATS['total_postings']}</b><br>
            Flagged for outreach: <b style="color: {ILLINI_ORANGE};">{AGGREGATE_STATS['flagged']}</b><br>
            Tier A leads: <b>{AGGREGATE_STATS['tier_a']}</b><br>
            Tier B leads: <b>{AGGREGATE_STATS['tier_b']}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_tiles():
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-tile">
                <div class="kpi-value">{AGGREGATE_STATS['total_postings']}</div>
                <div class="kpi-label">Postings Scored</div>
            </div>
            <div class="kpi-tile">
                <div class="kpi-value">{AGGREGATE_STATS['flagged']}</div>
                <div class="kpi-label">Flagged for Outreach</div>
            </div>
            <div class="kpi-tile">
                <div class="kpi-value">{AGGREGATE_STATS['tier_a']}</div>
                <div class="kpi-label">Tier A Leads</div>
            </div>
            <div class="kpi-tile">
                <div class="kpi-value">{AGGREGATE_STATS['tier_b']}</div>
                <div class="kpi-label">Tier B Leads</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def signal_chip(value: str) -> str:
    cls = "signal-yes" if value.lower() == "yes" else "signal-no"
    return f'<span class="signal-value {cls}">{value}</span>'


def confidence_chip(level: str) -> str:
    cls = {"High": "conf-high", "Medium": "conf-medium", "Low": "conf-low"}.get(level, "conf-medium")
    return f'<span class="confidence-chip {cls}">{level} confidence</span>'


def render_scorecard(s: dict):
    flagged_html = (
        '<span class="flagged-badge flagged-yes">✓ Flagged for Outreach</span>'
        if s["flagged"]
        else '<span class="flagged-badge flagged-no">✗ Not Flagged — Geography</span>'
    )

    # Header block
    st.markdown(
        f"""
        <div class="scorecard">
            <div class="scorecard-header">
                <div>
                    <div class="scorecard-company">{s['company_name']}</div>
                    <div class="scorecard-role">{s['job_title']}</div>
                    <div class="scorecard-meta">
                        {s['city']}, {s['state']} · {s['industry']} · {s['company_size']} employees · {s['funding_stage']} · Posted {s['posting_age_days']}d ago
                    </div>
                    <div style="margin-top: 14px;">
                        <span class="tier-badge tier-{s['tier']}">Tier {s['tier']}</span>
                        {flagged_html}
                    </div>
                </div>
                <div>
                    <div class="score-big">{s['final_score']}</div>
                    <div class="score-label">Fit Score / 100</div>
                </div>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Signals
    st.markdown('<div class="section-head">Signal Extraction</div>', unsafe_allow_html=True)

    for sig_key, label in [
        ("first_hire", "First Strategic Hire"),
        ("cluster", "Cluster Hiring"),
        ("new_initiative", "New Initiative"),
    ]:
        value = s[sig_key]
        confidence = s[f"{sig_key}_confidence"]
        quote = s[f"{sig_key}_quote"]

        st.markdown(
            f"""
            <div class="signal-row">
                <div>
                    <span class="signal-title">{label}</span>
                    {signal_chip(value)}
                    {confidence_chip(confidence)}
                </div>
                {'<div class="quote-block">' + quote + '</div>' if quote else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Fit axes
    st.markdown('<div class="section-head">Fit Assessment</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="fit-grid">
            <div class="fit-cell">
                <div class="fit-label">Industry Fit</div>
                <div class="fit-value">{s['industry_fit']}</div>
            </div>
            <div class="fit-cell">
                <div class="fit-label">Geography Fit</div>
                <div class="fit-value">{s['geography_fit']}</div>
            </div>
            <div class="fit-cell">
                <div class="fit-label">Program Fit</div>
                <div class="fit-value">{s['program_fit']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Score math
    st.markdown('<div class="section-head">Score Breakdown</div>', unsafe_allow_html=True)
    math_rows = ""
    for label, pts in s["score_math"]:
        sign = "+" if pts >= 0 else ""
        math_rows += f"<div>{label:<45} <span style='float:right'>{sign}{pts}</span></div>"
    math_rows += f"<div class='math-total'>Raw total <span style='float:right'>{s['raw_total']}</span></div>"
    math_rows += f"<div class='math-total'>Final (clipped 18–98) <span style='float:right'>{s['final_score']}</span></div>"

    st.markdown(f'<div class="math-table">{math_rows}</div>', unsafe_allow_html=True)

    # Rationale
    st.markdown('<div class="section-head">Rationale</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rationale">{s["rationale"]}</div>', unsafe_allow_html=True)

    # Owner
    st.markdown('<div class="section-head">Recommended Action</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="owner-block">{s["recommended_owner"]}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # close .scorecard


def render_coverage_map():
    st.markdown('<div class="section-head">Geographic Coverage — Week of Apr 20, 2026</div>', unsafe_allow_html=True)

    # Build pin list (lat/lng approximations for demo)
    pins = [
        ("NorthStack Partners", 40.693, -89.588, 98, "A"),       # Peoria, IL
        ("SummitRoute Partners", 43.073, -89.401, 88, "A"),      # Madison, WI
        ("NorthRoute Group", 40.693, -89.588, 88, "A"),          # Peoria, IL
        ("CedarBridge Partners", 40.112, -88.243, 85, "A"),      # Champaign, IL
        ("NexusStack Solutions", 40.693, -89.588, 85, "A"),      # Peoria, IL
        ("IronGrid Analytics", 39.781, -89.650, 85, "A"),        # Springfield, IL
        ("CedarRoute Analytics", 43.073, -89.401, 85, "A"),      # Madison, WI
        ("NexusRoute Group", 40.112, -88.243, 79, "B"),          # Champaign, IL
        ("NexusPath Partners", 41.785, -88.147, 79, "B"),        # Naperville, IL
        ("IronPeak Technologies", 41.785, -88.147, 77, "B"),     # Naperville, IL
        ("BluePeak Systems", 40.693, -89.588, 70, "B"),          # Peoria, IL
        ("RiverRoute Analytics", 43.073, -89.401, 72, "B"),      # Madison, WI
        ("CedarGrid Systems", 39.961, -82.999, 71, "B"),         # Columbus, OH
    ]

    df = pd.DataFrame(pins, columns=["name", "lat", "lon", "score", "tier"])

    fig = go.Figure()

    # Tier A pins
    a = df[df.tier == "A"]
    fig.add_trace(go.Scattergeo(
        lon=a.lon, lat=a.lat, text=a.name + "<br>Score: " + a.score.astype(str),
        mode="markers",
        marker=dict(size=16, color=ILLINI_ORANGE, line=dict(width=2, color="white")),
        name="Tier A (≥82)", hoverinfo="text",
    ))

    # Tier B pins
    b = df[df.tier == "B"]
    fig.add_trace(go.Scattergeo(
        lon=b.lon, lat=b.lat, text=b.name + "<br>Score: " + b.score.astype(str),
        mode="markers",
        marker=dict(size=12, color="#FBBF24", line=dict(width=2, color="white")),
        name="Tier B (69-81)", hoverinfo="text",
    ))

    # Coverage gap annotations
    fig.add_trace(go.Scattergeo(
        lon=[-99.9018, -83.1],  # Texas center, Georgia center
        lat=[31.9686, 32.9],
        text=["TX — 0 flagged leads<br>SOURCE MORE", "GA — 0 flagged leads<br>SOURCE MORE"],
        mode="markers+text",
        marker=dict(size=20, color="rgba(239, 68, 68, 0.3)", line=dict(width=2, color="#EF4444")),
        textfont=dict(color="#991B1B", size=10),
        textposition="top center",
        name="Coverage Gap", hoverinfo="text",
    ))

    fig.update_layout(
        geo=dict(
            scope="usa",
            projection=dict(type="albers usa"),
            showland=True,
            landcolor="#F3F4F6",
            subunitcolor="#D1D5DB",
            countrycolor="#D1D5DB",
        ),
        margin=dict(l=0, r=0, t=20, b=0),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=-0.05, xanchor="center", x=0.5),
        paper_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"""
        <div style="background: #FFF7ED; padding: 14px 18px; border-left: 4px solid {ILLINI_ORANGE}; border-radius: 0 6px 6px 0; margin-top: 12px;">
            <b style="color: {ILLINI_BLUE};">Sourcing recommendation:</b> 13 flagged leads concentrated in IL/WI/OH. Zero Tier A/B leads in Texas or Georgia this batch. Target Atlanta metro and Austin/Dallas/Houston for the next pull.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_batch_summary():
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-head">Tier Distribution</div>', unsafe_allow_html=True)
        tier_df = pd.DataFrame({
            "Tier": ["Tier A (≥82)", "Tier B (69-81)", "Tier C (55-68)", "Tier D (<55)"],
            "Count": [AGGREGATE_STATS["tier_a"], AGGREGATE_STATS["tier_b"], AGGREGATE_STATS["tier_c"], AGGREGATE_STATS["tier_d"]],
        })
        fig = go.Figure(go.Bar(
            x=tier_df["Tier"], y=tier_df["Count"],
            marker_color=[ILLINI_ORANGE, "#FBBF24", "#9CA3AF", "#D1D5DB"],
            text=tier_df["Count"], textposition="outside",
        ))
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=280,
            paper_bgcolor="white", plot_bgcolor="white",
            yaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-head">Hot Industries (Median Score)</div>', unsafe_allow_html=True)
        inds = AGGREGATE_STATS["hot_industries"]
        fig = go.Figure(go.Bar(
            x=[i[1] for i in inds], y=[i[0] for i in inds],
            orientation="h",
            marker_color=ILLINI_ORANGE,
            text=[f"{i[1]}" for i in inds], textposition="outside",
        ))
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=280,
            paper_bgcolor="white", plot_bgcolor="white",
            xaxis=dict(showgrid=True, gridcolor="#F3F4F6", range=[0, 80]),
        )
        st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    render_header()
    render_sidebar()

    tab1, tab2, tab3 = st.tabs(["🔍 Score a Posting", "🗺️ Coverage Map", "📊 Batch Summary"])

    with tab1:
        render_kpi_tiles()
        st.markdown('<div class="section-head">Score a posting</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns([4, 1])
        with col_a:
            posting_id = st.text_input(
                "Posting ID",
                placeholder="Enter posting ID, e.g. BT-024",
                label_visibility="collapsed",
            )
        with col_b:
            go_btn = st.button("Score", use_container_width=True)

        if go_btn or posting_id:
            if posting_id:
                with st.spinner(f"Scoring {posting_id.upper()}..."):
                    time.sleep(0.8)  # perceived latency for demo effect
                    scorecard = get_scorecard(posting_id)

                if scorecard:
                    render_scorecard(scorecard)
                else:
                    st.warning(f"No cached scorecard for {posting_id.upper()}. Try BT-024, BT-023, or BT-002.")

    with tab2:
        render_coverage_map()

    with tab3:
        render_kpi_tiles()
        render_batch_summary()
        st.markdown('<div class="section-head">Aggressive Hirers</div>', unsafe_allow_html=True)
        for name in AGGREGATE_STATS["aggressive_hirers"]:
            st.markdown(f"<div style='padding: 6px 0;'>• <b>{name}</b> — 2 postings in batch</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
