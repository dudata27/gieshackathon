"""
Magelli Prospect Identification Dashboard
Gies College of Business - AI for Impact Buildathon
LIVE INTEGRATION: calls Copilot Studio agent via Direct Line REST API.
"""

import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from agent_client import CopilotStudioAgent, DirectLineError
from parser import parse_scorecard
from file_handler import process_uploaded_file, truncate_text

ILLINI_ORANGE = "#E84A27"
ILLINI_BLUE = "#13294B"
OFF_WHITE = "#FAFAFA"

st.set_page_config(
    page_title="Magelli Prospect Identification",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = f"""
<style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    [data-testid="stSidebarNav"] {{display: none;}}
    [data-testid="stSidebarNavItems"] {{display: none;}}
    section[data-testid="stSidebar"] > div:first-child > div:first-child {{display: none;}}
    .stAppDeployButton {{display: none !important;}}
    button[kind="header"] {{display: none;}}
    [data-testid="collapsedControl"] {{color: white !important;}}
    [data-testid="collapsedControl"] svg {{fill: white !important;}}

    .stApp {{ background: {OFF_WHITE}; }}

    .magelli-header {{
        background: {ILLINI_BLUE};
        color: white;
        padding: 20px 32px;
        margin: 0 0 24px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 4px solid {ILLINI_ORANGE};
        border-radius: 6px;
    }}
    .magelli-header h1 {{
        color: white !important;
        font-size: 22px !important;
        font-weight: 700 !important;
        margin: 0 !important;
        padding: 0 !important;
        letter-spacing: -0.3px;
    }}
    .magelli-header .subtitle {{
        color: #BCC2CF;
        font-size: 13px;
        font-weight: 400;
        margin-top: 4px;
    }}
    .agent-status {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
        color: white;
        font-weight: 500;
    }}
    .status-dot {{
        width: 10px; height: 10px;
        background: #3DDC84;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0%   {{ box-shadow: 0 0 0 0 rgba(61, 220, 132, 0.7); }}
        70%  {{ box-shadow: 0 0 0 8px rgba(61, 220, 132, 0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(61, 220, 132, 0); }}
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        border-bottom: 2px solid #E5E7EB;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 24px;
        font-weight: 600;
        font-size: 14px;
        color: #6B7280;
        background: transparent;
    }}
    .stTabs [aria-selected="true"] {{
        color: {ILLINI_ORANGE} !important;
        border-bottom: 3px solid {ILLINI_ORANGE} !important;
        background: transparent !important;
    }}

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
        font-size: 22px; font-weight: 700;
        color: {ILLINI_BLUE}; margin: 0;
    }}
    .scorecard-role {{ font-size: 15px; color: #4B5563; margin-top: 4px; }}
    .scorecard-meta {{ font-size: 13px; color: #6B7280; margin-top: 8px; }}
    .score-big {{
        font-size: 56px; font-weight: 800;
        color: {ILLINI_ORANGE}; line-height: 1;
        text-align: right;
    }}
    .score-label {{
        font-size: 11px; color: #6B7280;
        text-transform: uppercase; letter-spacing: 1px;
        text-align: right; margin-top: 4px;
    }}

    .tier-badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px; font-weight: 700;
        letter-spacing: 1px; margin-right: 8px;
    }}
    .tier-A {{ background: {ILLINI_ORANGE}; color: white; }}
    .tier-B {{ background: #FBBF24; color: #1F2937; }}
    .tier-C {{ background: #9CA3AF; color: white; }}
    .tier-D {{ background: #D1D5DB; color: #4B5563; }}

    .flagged-badge {{
        display: inline-block; padding: 4px 12px;
        border-radius: 4px; font-size: 12px; font-weight: 600;
    }}
    .flagged-yes {{ background: #D1FAE5; color: #065F46; }}
    .flagged-no  {{ background: #FEE2E2; color: #991B1B; }}

    .signal-row {{ padding: 14px 0; border-bottom: 1px solid #F3F4F6; }}
    .signal-row:last-child {{ border-bottom: none; }}
    .signal-title {{
        font-size: 13px; font-weight: 600;
        color: {ILLINI_BLUE};
        text-transform: uppercase; letter-spacing: 0.5px;
    }}
    .signal-value {{
        display: inline-block; padding: 2px 10px;
        border-radius: 12px; font-size: 12px;
        font-weight: 600; margin-left: 8px;
    }}
    .signal-yes {{ background: {ILLINI_ORANGE}; color: white; }}
    .signal-no  {{ background: #E5E7EB; color: #4B5563; }}

    .confidence-chip {{
        display: inline-block; padding: 2px 8px;
        border-radius: 12px; font-size: 11px;
        font-weight: 500; margin-left: 6px;
    }}
    .conf-high   {{ background: #DBEAFE; color: #1E40AF; }}
    .conf-medium {{ background: #FEF3C7; color: #92400E; }}
    .conf-low    {{ background: #FEE2E2; color: #991B1B; }}

    .quote-block {{
        background: #F9FAFB;
        border-left: 3px solid {ILLINI_ORANGE};
        padding: 10px 14px; margin-top: 8px;
        font-size: 13px; color: #374151;
        font-style: italic;
        border-radius: 0 4px 4px 0;
    }}

    .fit-grid {{
        display: grid; grid-template-columns: repeat(3, 1fr);
        gap: 12px; margin: 20px 0;
    }}
    .fit-cell {{
        background: #F9FAFB; padding: 14px;
        border-radius: 6px; text-align: center;
    }}
    .fit-label {{
        font-size: 11px; color: #6B7280;
        text-transform: uppercase; letter-spacing: 1px;
    }}
    .fit-value {{
        font-size: 18px; font-weight: 700;
        color: {ILLINI_BLUE}; margin-top: 4px;
    }}

    .math-table {{
        background: #F9FAFB; padding: 16px 20px;
        border-radius: 6px;
        font-family: 'SF Mono', 'Consolas', monospace;
        font-size: 13px; color: #374151; line-height: 1.8;
    }}
    .math-total {{
        border-top: 2px solid #D1D5DB;
        margin-top: 8px; padding-top: 8px;
        font-weight: 700; color: {ILLINI_ORANGE};
    }}

    [data-testid="stSidebar"] {{ background: {ILLINI_BLUE}; }}
    [data-testid="stSidebar"] * {{ color: white !important; }}
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: white !important;
        border-bottom: 2px solid {ILLINI_ORANGE};
        padding-bottom: 6px;
    }}
    .lead-row {{
        padding: 10px 0;
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
        padding: 22px 24px;
        text-align: center;
    }}
    .kpi-value {{
        font-size: 36px; font-weight: 800;
        color: {ILLINI_ORANGE}; line-height: 1;
    }}
    .kpi-label {{
        font-size: 12px; color: #374151;
        text-transform: uppercase; letter-spacing: 1px;
        margin-top: 10px; font-weight: 600;
    }}

    .stTextInput input {{
        border: 2px solid {ILLINI_BLUE} !important;
        border-radius: 6px !important;
        font-size: 15px !important;
        padding: 10px !important;
        background: white !important;
        color: {ILLINI_BLUE} !important;
    }}
    .stTextInput input:focus {{
        border-color: {ILLINI_ORANGE} !important;
        box-shadow: 0 0 0 3px rgba(232, 74, 39, 0.15) !important;
    }}
    .stTextInput input::placeholder {{
        color: #9CA3AF !important;
    }}

    .stButton button {{
        background: {ILLINI_ORANGE} !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        border-radius: 6px !important;
        height: auto !important;
    }}
    .stButton button:hover {{
        background: #C13A1C !important;
    }}

    .section-head {{
        font-size: 14px;
        font-weight: 700;
        color: {ILLINI_BLUE};
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin: 24px 0 12px 0;
    }}

    .rationale {{
        background: #FFF7ED;
        border-left: 4px solid {ILLINI_ORANGE};
        padding: 14px 18px;
        border-radius: 0 6px 6px 0;
        font-size: 14px;
        color: {ILLINI_BLUE};
        line-height: 1.6;
        font-weight: 500;
    }}

    .owner-block {{
        background: {ILLINI_BLUE};
        color: white;
        padding: 14px 18px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
    }}

    .sourcing-callout {{
        background: #FFF7ED;
        padding: 16px 20px;
        border-left: 4px solid {ILLINI_ORANGE};
        border-radius: 0 6px 6px 0;
        margin-top: 12px;
        color: {ILLINI_BLUE};
        font-size: 14px;
        line-height: 1.6;
    }}
    .sourcing-callout b {{ color: {ILLINI_ORANGE}; }}

    .hirer-row {{
        background: white;
        padding: 14px 20px;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        margin: 8px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .hirer-name {{
        font-weight: 600;
        color: {ILLINI_BLUE};
        font-size: 15px;
    }}
    .hirer-badge {{
        background: {ILLINI_ORANGE};
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 700;
    }}

    .map-container {{
        background: white;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        margin-top: 12px;
    }}

    /* Radio labels in the main area */
    .stRadio > label,
    div[data-testid="stMarkdownContainer"] p {{
        color: {ILLINI_BLUE} !important;
    }}
    .stRadio div[role="radiogroup"] label {{
        color: {ILLINI_BLUE} !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }}
    .stRadio div[role="radiogroup"] label p {{
        color: {ILLINI_BLUE} !important;
    }}
    /* But keep sidebar radios white */
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stRadio label p {{
        color: white !important;
    }}

    /* File uploader styling */
    .stFileUploader label {{
        color: {ILLINI_BLUE} !important;
    }}
    .stFileUploader > div {{
        background: white !important;
        border: 2px dashed {ILLINI_BLUE} !important;
        border-radius: 8px !important;
    }}

    /* Selectbox */
    .stSelectbox label,
    .stSelectbox label p {{
        color: {ILLINI_BLUE} !important;
    }}

    /* Text area styling */
    .stTextArea textarea {{
        background: white !important;
        color: {ILLINI_BLUE} !important;
        border: 2px solid {ILLINI_BLUE} !important;
        border-radius: 6px !important;
        font-size: 14px !important;
    }}
    .stTextArea textarea::placeholder {{
        color: #9CA3AF !important;
    }}
    .stTextArea label,
    .stTextArea label p {{
        color: {ILLINI_BLUE} !important;
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

SCORECARDS = {
    "BT-024": {
        "posting_id": "BT-024",
        "company_name": "NorthStack Partners",
        "job_title": "Head of Growth",
        "city": "Peoria", "state": "IL",
        "industry": "HealthTech", "company_size": "1000+",
        "funding_stage": "Private Equity", "posting_age_days": 2,
        "first_hire": "Yes",
        "first_hire_quote": "this is the first dedicated leader for the team. You will establish the growth function, build the playbook, and set the operating cadence. We are looking for a founding team member who is comfortable building from the ground up.",
        "first_hire_confidence": "High",
        "cluster": "Yes",
        "cluster_quote": "As we scale the team, we are building out several adjacent functions in parallel and we are looking for leaders who are comfortable in a growing organization.",
        "cluster_confidence": "High",
        "new_initiative": "Yes",
        "new_initiative_quote": "In the next two quarters we are migrating our patient data platform to Snowflake, and this role will partner closely on that initiative.",
        "new_initiative_confidence": "High",
        "industry_fit": "High", "geography_fit": "Yes", "program_fit": "Strong",
        "final_score": 98, "tier": "A", "flagged": True,
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
        "recommended_owner": "Senior faculty advisor - contact this week",
    },
    "BT-023": {
        "posting_id": "BT-023",
        "company_name": "RiverBridge Systems",
        "job_title": "Director of Analytics",
        "city": "Boston", "state": "MA",
        "industry": "Consumer Goods", "company_size": "50-199",
        "funding_stage": "Series B", "posting_age_days": 17,
        "first_hire": "Yes",
        "first_hire_quote": "This is the first dedicated analytics hire on the team. You will build the analytics function from the ground up, establish playbooks, and own the roadmap. As a founding member of the function, you will have unusual latitude to set direction.",
        "first_hire_confidence": "High",
        "cluster": "Yes",
        "cluster_quote": "As we scale the team, we are building out several adjacent functions in parallel and we are looking for leaders who are comfortable in a growing organization.",
        "cluster_confidence": "High",
        "new_initiative": "No", "new_initiative_quote": "", "new_initiative_confidence": "High",
        "industry_fit": "High", "geography_fit": "No", "program_fit": "Strong",
        "final_score": 79, "tier": "B", "flagged": False,
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
        "recommended_owner": "Not flagged - geography outside IL/WI/IN/IA/MN/OH/MI/MO target region",
    },
    "BT-002": {
        "posting_id": "BT-002",
        "company_name": "CedarBridge Partners",
        "job_title": "Director of Revenue Operations",
        "city": "Champaign", "state": "IL",
        "industry": "HealthTech", "company_size": "200-499",
        "funding_stage": "Private Equity", "posting_age_days": 17,
        "first_hire": "Yes",
        "first_hire_quote": "we are establishing our RevOps function and looking for the first dedicated leader to build the practice from scratch.",
        "first_hire_confidence": "High",
        "cluster": "No", "cluster_quote": "", "cluster_confidence": "High",
        "new_initiative": "Yes",
        "new_initiative_quote": "launching our partner channel in Q3 and this role will own the supporting revenue infrastructure.",
        "new_initiative_confidence": "High",
        "industry_fit": "High", "geography_fit": "Yes", "program_fit": "Strong",
        "final_score": 85, "tier": "A", "flagged": True,
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
        "recommended_owner": "Senior faculty advisor - contact this week",
    },
}

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

AGGRESSIVE_HIRERS = [
    ("IronPeak Technologies", 2),
    ("RiverBridge Systems", 2),
    ("CedarRoute Partners", 2),
    ("NorthStack Partners", 2),
    ("NexusPath Partners", 2),
]

AGGREGATE_STATS = {
    "total_postings": 64,
    "flagged": 13,
    "tier_a": 7,
    "tier_b": 12,
    "tier_c": 14,
    "tier_d": 31,
    "hot_industries": [("Retail", 67.5), ("FinTech", 67.0), ("Logistics", 65.0)],
}


def get_scorecard(posting_id: str):
    return SCORECARDS.get(posting_id.upper().strip())


def signal_chip(value: str) -> str:
    cls = "signal-yes" if value.lower() == "yes" else "signal-no"
    return f'<span class="signal-value {cls}">{value}</span>'


def confidence_chip(level: str) -> str:
    cls = {"High": "conf-high", "Medium": "conf-medium", "Low": "conf-low"}.get(level, "conf-medium")
    return f'<span class="confidence-chip {cls}">{level} confidence</span>'


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
                <span>Agent: LIVE · Copilot Studio · Claude Opus 4.6</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    st.sidebar.markdown("### Top Flagged Leads")
    st.sidebar.markdown(
        "<div style='font-size: 12px; color: #BCC2CF; margin-bottom: 12px;'>This week's batch · Midwest only</div>",
        unsafe_allow_html=True,
    )

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


def render_scorecard(s):
    flagged_html = (
        '<span class="flagged-badge flagged-yes">✓ Flagged for Outreach</span>'
        if s["flagged"]
        else '<span class="flagged-badge flagged-no">✗ Not Flagged — Geography</span>'
    )

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

    st.markdown('<div class="section-head">Signal Extraction</div>', unsafe_allow_html=True)

    for sig_key, label in [
        ("first_hire", "First Strategic Hire"),
        ("cluster", "Cluster Hiring"),
        ("new_initiative", "New Initiative"),
    ]:
        value = s[sig_key]
        confidence = s[f"{sig_key}_confidence"]
        quote = s[f"{sig_key}_quote"]
        quote_html = f'<div class="quote-block">{quote}</div>' if quote else ""

        st.markdown(
            f"""
            <div class="signal-row">
                <div>
                    <span class="signal-title">{label}</span>
                    {signal_chip(value)}
                    {confidence_chip(confidence)}
                </div>
                {quote_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

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

    st.markdown('<div class="section-head">Score Breakdown</div>', unsafe_allow_html=True)
    math_rows = ""
    for label, pts in s["score_math"]:
        sign = "+" if pts >= 0 else ""
        math_rows += f"<div>{label} <span style='float:right'>{sign}{pts}</span></div>"
    math_rows += f"<div class='math-total'>Raw total <span style='float:right'>{s['raw_total']}</span></div>"
    math_rows += f"<div class='math-total'>Final (clipped 18-98) <span style='float:right'>{s['final_score']}</span></div>"
    st.markdown(f'<div class="math-table">{math_rows}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-head">Rationale</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="rationale">{s["rationale"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-head">Recommended Action</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="owner-block">{s["recommended_owner"]}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_coverage_map():
    st.markdown('<div class="section-head">Geographic Coverage — Week of Apr 20, 2026</div>', unsafe_allow_html=True)

    pins = [
        ("NorthStack Partners", 40.693, -89.588, 98, "A"),
        ("SummitRoute Partners", 43.073, -89.401, 88, "A"),
        ("NorthRoute Group", 40.693, -89.588, 88, "A"),
        ("CedarBridge Partners", 40.112, -88.243, 85, "A"),
        ("NexusStack Solutions", 40.693, -89.588, 85, "A"),
        ("IronGrid Analytics", 39.781, -89.650, 85, "A"),
        ("CedarRoute Analytics", 43.073, -89.401, 85, "A"),
        ("NexusRoute Group", 40.112, -88.243, 79, "B"),
        ("NexusPath Partners", 41.785, -88.147, 79, "B"),
        ("IronPeak Technologies", 41.785, -88.147, 77, "B"),
        ("BluePeak Systems", 40.693, -89.588, 70, "B"),
        ("RiverRoute Analytics", 43.073, -89.401, 72, "B"),
        ("CedarGrid Systems", 39.961, -82.999, 71, "B"),
    ]

    df = pd.DataFrame(pins, columns=["name", "lat", "lon", "score", "tier"])
    fig = go.Figure()

    a = df[df.tier == "A"]
    fig.add_trace(go.Scattergeo(
        lon=a.lon, lat=a.lat,
        text=a.name + "<br>Score: " + a.score.astype(str),
        mode="markers",
        marker=dict(size=18, color=ILLINI_ORANGE, line=dict(width=2, color="white")),
        name="Tier A (≥82)",
        hoverinfo="text",
    ))

    b = df[df.tier == "B"]
    fig.add_trace(go.Scattergeo(
        lon=b.lon, lat=b.lat,
        text=b.name + "<br>Score: " + b.score.astype(str),
        mode="markers",
        marker=dict(size=14, color="#FBBF24", line=dict(width=2, color="white")),
        name="Tier B (69-81)",
        hoverinfo="text",
    ))

    fig.add_trace(go.Scattergeo(
        lon=[-99.9018, -83.1],
        lat=[31.9686, 32.9],
        text=["Texas — 0 flagged", "Georgia — 0 flagged"],
        mode="markers",
        marker=dict(size=28, color="rgba(239, 68, 68, 0.25)", line=dict(width=2, color="#EF4444")),
        name="Coverage Gap",
        hoverinfo="text",
    ))

    fig.update_layout(
        geo=dict(
            scope="usa",
            projection=dict(type="albers usa"),
            showland=True,
            landcolor="#F3F4F6",
            subunitcolor="#D1D5DB",
            countrycolor="#D1D5DB",
            bgcolor="white",
        ),
        margin=dict(l=0, r=0, t=10, b=60),
        height=480,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=13, color=ILLINI_BLUE, family="sans-serif"),
            bgcolor="white",
            bordercolor="#E5E7EB",
            borderwidth=1,
        ),
        paper_bgcolor="white",
    )

    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="sourcing-callout">
            <b>Sourcing recommendation:</b><br>
            13 flagged leads concentrated in IL, WI, and OH. Zero Tier A or B leads in Texas or Georgia this batch.
            Target Atlanta metro and Austin, Dallas, Houston for the next pull.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_batch_summary():
    render_kpi_tiles()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-head">Tier Distribution</div>', unsafe_allow_html=True)
        tier_df = pd.DataFrame({
            "Tier": ["Tier A", "Tier B", "Tier C", "Tier D"],
            "Count": [AGGREGATE_STATS["tier_a"], AGGREGATE_STATS["tier_b"],
                      AGGREGATE_STATS["tier_c"], AGGREGATE_STATS["tier_d"]],
        })
        fig = go.Figure(go.Bar(
            x=tier_df["Tier"], y=tier_df["Count"],
            marker_color=[ILLINI_ORANGE, "#FBBF24", "#9CA3AF", "#D1D5DB"],
            text=tier_df["Count"], textposition="outside",
            textfont=dict(size=14, color=ILLINI_BLUE, family="sans-serif"),
        ))
        fig.update_layout(
            margin=dict(l=40, r=20, t=20, b=40),
            height=300,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                tickfont=dict(size=13, color=ILLINI_BLUE, family="sans-serif"),
                showgrid=False,
            ),
            yaxis=dict(
                tickfont=dict(size=12, color="#6B7280"),
                showgrid=True,
                gridcolor="#F3F4F6",
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-head">Hot Industries (Median Score)</div>', unsafe_allow_html=True)
        inds = AGGREGATE_STATS["hot_industries"]
        fig = go.Figure(go.Bar(
            x=[i[1] for i in inds],
            y=[i[0] for i in inds],
            orientation="h",
            marker_color=ILLINI_ORANGE,
            text=[f"{i[1]}" for i in inds],
            textposition="outside",
            textfont=dict(size=14, color=ILLINI_BLUE, family="sans-serif"),
        ))
        fig.update_layout(
            margin=dict(l=80, r=40, t=20, b=40),
            height=300,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis=dict(
                range=[0, 80],
                tickfont=dict(size=12, color="#6B7280"),
                showgrid=True,
                gridcolor="#F3F4F6",
            ),
            yaxis=dict(
                tickfont=dict(size=13, color=ILLINI_BLUE, family="sans-serif"),
                showgrid=False,
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-head">Aggressive Hirers — 2+ Postings in Batch</div>', unsafe_allow_html=True)
    for name, count in AGGRESSIVE_HIRERS:
        st.markdown(
            f"""
            <div class="hirer-row">
                <span class="hirer-name">{name}</span>
                <span class="hirer-badge">{count} POSTINGS</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    render_header()
    render_sidebar()

    tab1, tab2, tab3 = st.tabs(["Score a Posting", "Coverage Map", "Batch Summary"])

    with tab1:
        render_kpi_tiles()

        st.markdown('<div class="section-head">Score a Job Posting</div>', unsafe_allow_html=True)

        input_mode = st.radio(
            "Input method",
            ["Paste text", "Upload file", "Corpus posting ID"],
            horizontal=True,
            label_visibility="collapsed",
            key="input_mode",
        )

        # For each mode, collect (display_id, text_to_send, is_id_lookup)
        score_target = None

        if input_mode == "Paste text":
            posting_text = st.text_area(
                "Job posting text",
                placeholder=(
                    "Paste the full job posting here. Include company name, role title, "
                    "location, and the full description. Example:\n\n"
                    "NorthStack Partners is hiring a Head of Growth in Peoria, IL. "
                    "Following recent investment, we are formalizing our growth function "
                    "and this is the first dedicated leader for the team..."
                ),
                height=200,
                label_visibility="collapsed",
                key="posting_text",
            )
            if st.button("Score this posting", key="score_text_btn"):
                if posting_text and posting_text.strip():
                    text = posting_text.strip()
                    # Auto-detect: if user pasted just a BT-ID, treat as ID lookup
                    import re as _re
                    id_match = _re.match(r"^(BT-\d+)\s*$", text, _re.IGNORECASE)
                    if id_match:
                        score_target = (id_match.group(1).upper(), id_match.group(1).upper(), True)
                    else:
                        score_target = ("Pasted posting", text, False)
                else:
                    st.warning("Please paste a job posting first.")

        elif input_mode == "Upload file":
            uploaded = st.file_uploader(
                "Upload a job posting file",
                type=["xlsx", "xls", "csv", "pdf", "docx", "txt", "md"],
                label_visibility="collapsed",
                help="Supports Excel, CSV, PDF, Word, text, and markdown files.",
                key="posting_upload",
            )

            if uploaded is not None:
                try:
                    result = process_uploaded_file(uploaded.name, uploaded.getvalue())
                except Exception as e:
                    st.error(f"Could not read file: {e}")
                    result = None

                if result and result["mode"] == "multi":
                    postings = result["postings"]
                    st.success(f"Loaded {len(postings)} postings from {uploaded.name}")

                    # Let user pick one to score
                    labels = [p["label"] for p in postings]
                    pick = st.selectbox(
                        "Select a posting to score",
                        options=range(len(postings)),
                        format_func=lambda i: labels[i],
                        key="posting_pick",
                    )

                    with st.expander(f"Preview: {postings[pick]['label']}"):
                        st.text(postings[pick]["text"][:800])

                    if st.button("Score selected posting", key="score_upload_btn"):
                        selected = postings[pick]
                        score_target = (selected["id"] or selected["label"], selected["text"], False)

                elif result and result["mode"] == "single":
                    st.success(f"Loaded {uploaded.name}")
                    text = result["text"]
                    if not text or len(text.strip()) < 50:
                        st.warning("File appears empty or too short.")
                    else:
                        with st.expander(f"Preview ({len(text)} characters)"):
                            st.text(text[:800])
                        if st.button("Score this posting", key="score_file_btn"):
                            score_target = (uploaded.name, text, False)

        else:  # Corpus posting ID
            col_a, col_b = st.columns([5, 1])
            with col_a:
                corpus_id = st.text_input(
                    "Posting ID",
                    placeholder="Enter a corpus posting ID, e.g. BT-024",
                    label_visibility="collapsed",
                    key="corpus_id_input",
                )
            with col_b:
                if st.button("Score", use_container_width=True, key="score_id_btn"):
                    if corpus_id and corpus_id.strip():
                        pid = corpus_id.strip().upper()
                        score_target = (pid, pid, True)
                    else:
                        st.warning("Enter a posting ID first.")

        # ─── Score whatever was set above ────────────────────────────
        if score_target is not None:
            display_id, text_to_send, is_id_lookup = score_target

            # Demo safety net — if it's an ID we have cached, render instantly
            if is_id_lookup:
                cached = SCORECARDS.get(display_id.upper())
                if cached:
                    render_scorecard(cached)
                    score_target = None  # suppress live call

            if score_target is not None:
                secret = st.secrets.get("COPILOT_SECRET", "")
                if not secret:
                    st.error("Agent secret not configured. Set COPILOT_SECRET in Streamlit Cloud secrets.")
                else:
                    spinner_label = (
                        f"Scoring {display_id} with Copilot Studio agent..."
                        if is_id_lookup
                        else "Analyzing the posting with Copilot Studio agent..."
                    )
                    with st.spinner(spinner_label):
                        try:
                            agent = CopilotStudioAgent(secret)
                            agent.start_conversation()

                            if is_id_lookup:
                                prompt = f"score {display_id}"
                            else:
                                safe_text = truncate_text(text_to_send, max_chars=4000)
                                prompt = f"Score this job posting:\n\n{safe_text}"

                            reply = agent.ask(prompt, max_wait_sec=75)
                            scorecard = parse_scorecard(display_id, reply)
                            if scorecard["final_score"] == 0:
                                st.warning(
                                    "Agent responded but I couldn't parse a score cleanly. Raw output below."
                                )
                                st.code(reply, language="markdown")
                            else:
                                render_scorecard(scorecard)
                                with st.expander("Raw agent response"):
                                    st.code(reply, language="markdown")
                        except DirectLineError as e:
                            st.error(f"Agent call failed: {e}")
                        except Exception as e:
                            st.error(f"Unexpected error: {type(e).__name__}: {e}")

    with tab2:
        render_coverage_map()

    with tab3:
        render_batch_summary()


if __name__ == "__main__":
    main()
