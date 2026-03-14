"""Streamlit frontend for browsing, comparing, and ingesting candidates.

The UI is intentionally thin: it delegates business logic to the FastAPI backend
and focuses on recruiter-friendly workflows such as search, profile review,
pipeline management, and ingestion triggers.
"""

import os
from collections import Counter

import requests
import streamlit as st

# In Docker Compose this is injected as `http://api:8000`; locally it falls back
# to the developer's loopback address.
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"]

st.set_page_config(page_title="TalentFlow AI", page_icon="✦", layout="wide")


def fetch_candidates(skill=None, location=None, min_exp=None):
    """Fetch candidate list data from the backend with optional filters."""
    params = {}
    if skill:
        params["skill"] = skill
    if location:
        params["location"] = location
    if min_exp:
        params["min_exp"] = min_exp

    try:
        response = requests.get(f"{API_URL}/candidates", params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        # The UI degrades gracefully by showing an empty state instead of crashing.
        return []


def fetch_candidate(candidate_id):
    """Fetch one candidate profile by identifier."""
    try:
        response = requests.get(f"{API_URL}/candidates/{candidate_id}", timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def update_stage(candidate_id, stage):
    """Persist a pipeline stage change through the backend API."""
    try:
        response = requests.patch(
            f"{API_URL}/candidates/{candidate_id}/stage",
            params={"stage": stage},
            timeout=20,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def source_badge(source):
    """Return a small emoji badge used to quickly identify a candidate source."""
    colors = {
        "resume": "🔵",
        "bamboohr": "🟢",
        "gmail": "🔴",
        "linkedin": "🟡",
    }
    return colors.get(source, "⚪")


def stage_color(stage):
    """Map stage names to the UI colors used across list/profile/kanban views."""
    colors = {
        "applied": "#888780",
        "screening": "#185FA5",
        "interview": "#854F0B",
        "offer": "#534AB7",
        "hired": "#0F6E56",
        "rejected": "#A32D2D",
    }
    return colors.get(stage, "#888780")


def inject_global_styles():
    """Apply the editorial dark/zinc design language across the Streamlit app."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&family=Outfit:wght@300;400;500;600;700&display=swap');

        :root {
            --tf-bg: #09090b;
            --tf-surface: rgba(24, 24, 27, 0.64);
            --tf-surface-strong: rgba(39, 39, 42, 0.82);
            --tf-border: rgba(255, 255, 255, 0.10);
            --tf-border-strong: rgba(45, 212, 191, 0.25);
            --tf-text: #f4f4f5;
            --tf-muted: #a1a1aa;
            --tf-ghost: #71717a;
            --tf-primary: #0d9488;
            --tf-primary-bright: #2dd4bf;
            --tf-linkedin: #0A66C2;
            --tf-gmail: #0d9488;
            --tf-hrms: #059669;
            --tf-resume: #f97316;
        }

        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
        }

        .stApp {
            color: var(--tf-text);
            background:
                radial-gradient(circle at top left, rgba(45, 212, 191, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(13, 148, 136, 0.12), transparent 24%),
                linear-gradient(180deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0)),
                var(--tf-bg);
            overflow-x: hidden;
        }

        [data-testid="stAppViewContainer"] {
            background: transparent;
            overflow-x: hidden;
        }

        [data-testid="block-container"] {
            max-width: 1280px;
            padding-top: 1.25rem;
            padding-bottom: 2.75rem;
            padding-left: clamp(1rem, 2.5vw, 2rem);
            padding-right: clamp(1rem, 2.5vw, 2rem);
        }

        [data-testid="stHorizontalBlock"] {
            gap: 1.05rem;
            align-items: stretch;
        }

        [data-testid="column"] > div {
            width: 100%;
        }

        header[data-testid="stHeader"] {
            background: rgba(9, 9, 11, 0.65);
            backdrop-filter: blur(10px);
        }

        section[data-testid="stSidebar"] {
            min-width: 268px !important;
            max-width: 268px !important;
            border-right: 1px solid var(--tf-border);
            background:
                radial-gradient(circle at top, rgba(45, 212, 191, 0.14), transparent 28%),
                linear-gradient(180deg, rgba(24, 24, 27, 0.95), rgba(9, 9, 11, 0.95));
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 1.25rem;
        }

        h1, h2, h3, h4 {
            font-family: 'Bricolage Grotesque', sans-serif !important;
            letter-spacing: -0.03em;
            color: var(--tf-text);
        }

        p, li, label, .stCaption {
            color: var(--tf-text);
        }

        small, code, .tf-kicker, .tf-status, .tf-meta {
            font-family: 'JetBrains Mono', monospace !important;
        }

        .tf-shell,
        .tf-card,
        [data-testid="stMetric"],
        [data-testid="stForm"] {
            border: 1px solid var(--tf-border);
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
            backdrop-filter: blur(16px);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }

        .tf-shell {
            border-radius: 24px;
            padding: 2rem;
            min-height: 100%;
            margin-bottom: 1rem;
        }

        .tf-card {
            border-radius: 20px;
            padding: 1.25rem;
            min-height: 100%;
            transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
            margin-bottom: 1rem;
            overflow: hidden;
        }

        .tf-card:hover {
            transform: scale(1.01);
            border-color: var(--tf-border-strong);
            box-shadow: 0 0 0 1px rgba(45, 212, 191, 0.08), 0 16px 48px rgba(0, 0, 0, 0.20);
        }

        .tf-kicker {
            color: var(--tf-primary-bright);
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            margin-bottom: 0.9rem;
        }

        .tf-hero-title {
            font-family: 'Bricolage Grotesque', sans-serif;
            font-size: clamp(3rem, 6vw, 4.85rem);
            font-weight: 700;
            line-height: 1.05;
            letter-spacing: -0.04em;
            margin: 0;
        }

        .tf-lead {
            color: var(--tf-muted);
            font-size: 1.08rem;
            line-height: 1.8;
            margin: 1rem 0 1.5rem;
            max-width: 42rem;
        }

        .tf-inline-meta {
            display: flex;
            gap: 0.65rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }

        .tf-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.03);
            color: var(--tf-muted);
            padding: 0.35rem 0.8rem;
            font-size: 0.8rem;
            line-height: 1.35;
            white-space: normal;
            word-break: break-word;
        }

        .tf-section-heading {
            font-family: 'Bricolage Grotesque', sans-serif;
            font-size: 1.9rem;
            font-weight: 600;
            letter-spacing: -0.02em;
            margin: 0;
        }

        .tf-section-copy {
            color: var(--tf-muted);
            max-width: 52rem;
            line-height: 1.75;
            margin: 0.4rem 0 1.2rem;
        }

        .tf-card-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.9rem;
            margin-bottom: 1rem;
        }

        .tf-icon {
            width: 3rem;
            height: 3rem;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .tf-icon.resume {
            background: rgba(249, 115, 22, 0.16);
            color: #fdba74;
        }

        .tf-icon.linkedin {
            background: rgba(10, 102, 194, 0.18);
            color: #93c5fd;
        }

        .tf-icon.gmail {
            background: rgba(13, 148, 136, 0.18);
            color: #99f6e4;
        }

        .tf-icon.hrms {
            background: rgba(5, 150, 105, 0.18);
            color: #86efac;
        }

        .tf-status {
            border-radius: 999px;
            padding: 0.3rem 0.7rem;
            font-size: 0.68rem;
            font-weight: 600;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .tf-status.connected {
            color: #99f6e4;
            background: rgba(13, 148, 136, 0.14);
            border: 1px solid rgba(45, 212, 191, 0.24);
        }

        .tf-status.available {
            color: #d4d4d8;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .tf-card h3,
        .tf-card h4 {
            margin: 0 0 0.4rem;
            font-size: 1.2rem;
        }

        .tf-card p {
            color: var(--tf-muted);
            line-height: 1.7;
            margin-bottom: 0;
        }

        .tf-card-footer {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            align-items: center;
            margin-top: 1rem;
            flex-wrap: wrap;
        }

        .tf-link {
            color: var(--tf-primary-bright);
            font-size: 0.85rem;
        }

        .tf-stat-value {
            font-family: 'Bricolage Grotesque', sans-serif;
            font-size: 2.4rem;
            font-weight: 700;
            line-height: 1;
            letter-spacing: -0.04em;
            margin: 0.35rem 0 0.75rem;
        }

        .tf-stage-grid {
            display: grid;
            gap: 0.7rem;
            margin-top: 1rem;
        }

        .tf-stage-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.8rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.03);
            padding: 0.8rem 1rem;
        }

        .tf-stage-row span {
            color: var(--tf-muted);
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.18em;
        }

        .tf-stage-row strong {
            font-family: 'Bricolage Grotesque', sans-serif;
            font-size: 1.15rem;
            line-height: 1;
        }

        .stButton > button {
            position: relative;
            overflow: hidden;
            border-radius: 14px;
            border: 1px solid rgba(45, 212, 191, 0.35);
            background: linear-gradient(90deg, rgba(13, 148, 136, 0.95), rgba(45, 212, 191, 0.92));
            color: white;
            font-weight: 600;
            min-height: 2.9rem;
            padding: 0.55rem 0.9rem;
            white-space: normal;
            transition: all 0.3s ease-in-out;
            box-shadow: 0 0 0 rgba(45, 212, 191, 0);
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(153, 246, 228, 0.7);
            box-shadow: 0 0 34px rgba(45, 212, 191, 0.28), 0 0 80px rgba(45, 212, 191, 0.12);
        }

        .stButton > button:focus {
            border-color: rgba(153, 246, 228, 0.9);
            box-shadow: 0 0 0 1px rgba(45, 212, 191, 0.28), 0 0 28px rgba(45, 212, 191, 0.22);
        }

        .stTextInput input,
        .stNumberInput input,
        .stSelectbox [data-baseweb="select"] > div,
        .stFileUploader > div,
        .stTextArea textarea {
            border-radius: 14px !important;
            border: 1px solid rgba(255, 255, 255, 0.10) !important;
            background: rgba(24, 24, 27, 0.68) !important;
            color: var(--tf-text) !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            padding-bottom: 0.25rem;
            flex-wrap: wrap;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            color: var(--tf-muted);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        .stTabs [aria-selected="true"] {
            color: white !important;
            background: rgba(13, 148, 136, 0.22) !important;
            border-color: rgba(45, 212, 191, 0.28) !important;
        }

        .stAlert {
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        hr {
            border-color: rgba(255, 255, 255, 0.08);
        }

        @media (max-width: 1200px) {
            section[data-testid="stSidebar"] {
                min-width: 252px !important;
                max-width: 252px !important;
            }

            [data-testid="block-container"] {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .tf-hero-title {
                font-size: clamp(2.3rem, 7vw, 3.35rem);
            }
        }

        @media (max-width: 900px) {
            [data-testid="stHorizontalBlock"] {
                gap: 0.8rem;
            }

            .tf-shell,
            .tf-card {
                padding: 1rem;
                border-radius: 16px;
            }

            .tf-inline-meta {
                gap: 0.45rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def navigate_to(target_page):
    """Programmatically switch pages from CTA buttons on the landing page."""
    st.session_state["page_override"] = target_page
    st.rerun()


def render_stat_card(label, value, caption):
    """Render a compact glassmorphic metric card."""
    st.markdown(
        f"""
        <div class="tf-card">
            <div class="tf-kicker">{label}</div>
            <div class="tf-stat-value">{value}</div>
            <p>{caption}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_integration_card(name, icon_class, symbol, detail, metric, connected=False):
    """Render one source/integration card for the landing page grid."""
    status = "Connected" if connected else "Available"
    status_class = "connected" if connected else "available"
    st.markdown(
        f"""
        <div class="tf-card">
            <div class="tf-card-row">
                <div class="tf-icon {icon_class}">{symbol}</div>
                <div class="tf-status {status_class}">{status}</div>
            </div>
            <h3>{name}</h3>
            <p>{detail}</p>
            <div class="tf-card-footer">
                <span class="tf-chip">{metric}</span>
                <span class="tf-link">Signal layer</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_page():
    """Render the editorial landing page for the recruiter control center."""
    candidates = fetch_candidates()
    stage_counts = Counter((candidate.get("stage") or "applied") for candidate in candidates)
    source_counts = Counter((candidate.get("source") or "resume") for candidate in candidates)

    active_pipeline = sum(stage_counts.get(stage, 0) for stage in ["screening", "interview", "offer"])
    connected_sources = sum(1 for source in ["resume", "linkedin", "gmail", "bamboohr"] if source_counts.get(source, 0))
    control_status = "LIVE DATA PLANE" if candidates else "OFFLINE READY"
    control_caption = (
        "Backend connected. Real recruiter workflows are ready for search, review, and stage movement."
        if candidates
        else "The shell still loads without backend availability so you can present the experience safely."
    )
    lead_stage = stage_counts.most_common(1)[0][0].upper() if stage_counts else "STANDBY"

    hero_left, hero_right = st.columns([1.1, 0.9], gap="large")
    with hero_left:
        st.markdown(
            f"""
            <div class="tf-shell">
                <div class="tf-kicker">NEXUS INTELLIGENCE // TALENTFLOW AI</div>
                <h1 class="tf-hero-title">Zero-Waste Hiring.</h1>
                <p class="tf-lead">
                    Orchestrate resume intake, semantic search, HR sync, and shortlist decisions inside
                    one dark editorial control surface built for fast recruiter movement.
                </p>
                <div class="tf-inline-meta">
                    <span class="tf-chip">12-column editorial layout</span>
                    <span class="tf-chip">Glass surfaces + neon CTA glow</span>
                    <span class="tf-chip">Post-SaaS operating system voice</span>
                </div>
                <div class="tf-inline-meta" style="margin-top:1.15rem;">
                    <span class="tf-chip tf-meta">{control_status}</span>
                    <span class="tf-chip tf-meta">Primary accent // teal 172°</span>
                    <span class="tf-chip tf-meta">Fonts // Bricolage, Outfit, JetBrains Mono</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cta1, cta2, cta3 = st.columns(3)
        with cta1:
            if st.button("Launch Control Center", key="home_launch_candidates", use_container_width=True):
                navigate_to("📋 Candidates")
        with cta2:
            if st.button("Connect Intake", key="home_launch_ingest", use_container_width=True):
                navigate_to("📥 Ingest")
        with cta3:
            if st.button("Review Pipeline", key="home_launch_pipeline", use_container_width=True):
                navigate_to("📌 Pipeline")

    with hero_right:
        metric_row_a = st.columns(2)
        with metric_row_a[0]:
            render_stat_card("candidate index", len(candidates), "Profiles available for browse, compare, and profile review.")
        with metric_row_a[1]:
            render_stat_card("active funnel", active_pipeline, "Candidates currently inside screening, interview, or offer loops.")

        metric_row_b = st.columns(2)
        with metric_row_b[0]:
            render_stat_card("connected intake", f"{connected_sources}/4", control_caption)
        with metric_row_b[1]:
            render_stat_card("dominant stage", lead_stage, "Current pipeline gravity based on indexed recruiter data.")

    st.markdown(
        """
        <div style="margin: 2.75rem 0 0.35rem;">
            <div class="tf-kicker">SIGNAL MESH</div>
            <h2 class="tf-section-heading">Intake that stays context-aware.</h2>
            <p class="tf-section-copy">
                Source-native cards mirror the Nexus aesthetic while mapping directly to the ingest and sync flows already present in this app.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    source_columns = st.columns(4, gap="large")
    with source_columns[0]:
        render_integration_card(
            "Resume Upload",
            "resume",
            "📄",
            "Route recruiter-submitted PDFs through structured parsing and normalized skill extraction.",
            f"{source_counts.get('resume', 0)} indexed",
            connected=source_counts.get("resume", 0) > 0,
        )
    with source_columns[1]:
        render_integration_card(
            "LinkedIn Intake",
            "linkedin",
            "in",
            "Turn profile payloads into search-ready candidate records with role and experience normalization.",
            f"{source_counts.get('linkedin', 0)} indexed",
            connected=source_counts.get("linkedin", 0) > 0,
        )
    with source_columns[2]:
        render_integration_card(
            "Gmail Resume Sync",
            "gmail",
            "✉",
            "Sweep inbox attachments, rank likely resumes, and ingest only high-signal submissions.",
            f"{source_counts.get('gmail', 0)} indexed",
            connected=source_counts.get("gmail", 0) > 0,
        )
    with source_columns[3]:
        render_integration_card(
            "BambooHR Sync",
            "hrms",
            "HR",
            "Bridge the recruiter workflow with downstream HR records for closing the hiring loop.",
            f"{source_counts.get('bamboohr', 0)} indexed",
            connected=source_counts.get("bamboohr", 0) > 0,
        )

    control_left, control_right = st.columns([1.1, 0.9], gap="large")
    stage_rows = "".join(
        f'<div class="tf-stage-row"><span>{stage.upper()}</span><strong>{stage_counts.get(stage, 0)}</strong></div>'
        for stage in STAGES
    )

    with control_left:
        st.markdown(
            f"""
            <div class="tf-card">
                <div class="tf-kicker">CONTROL SURFACE</div>
                <h3>Pipeline visibility without noise.</h3>
                <p>
                    The app already supports page-level review, comparison, and stage movement. This bento panel surfaces the funnel as an operational brief.
                </p>
                <div class="tf-stage-grid">{stage_rows}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with control_right:
        st.markdown(
            """
            <div class="tf-card" style="margin-bottom: 1rem;">
                <div class="tf-kicker">SEMANTIC SEARCH</div>
                <h3>Rank by meaning.</h3>
                <p>
                    Use natural-language queries to pull candidates by inferred fit, not just exact keyword overlap.
                </p>
                <div class="tf-card-footer">
                    <span class="tf-chip">Example // backend engineer with startup experience</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="tf-card">
                <div class="tf-kicker">DECISION LOOPS</div>
                <h3>Compare. Advance. Sync.</h3>
                <p>
                    Move from shortlist evaluation to HR handoff with fewer tabs, clearer stage ownership, and consistent source context.
                </p>
                <div class="tf-card-footer">
                    <span class="tf-chip">Profile review</span>
                    <span class="tf-chip">Candidate compare</span>
                    <span class="tf-chip">HRMS push</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    action_row = st.columns(3, gap="large")
    with action_row[0]:
        if st.button("Open Profiles", key="home_profiles", use_container_width=True):
            navigate_to("👤 Profile")
    with action_row[1]:
        if st.button("Compare Talent", key="home_compare", use_container_width=True):
            navigate_to("⚖️ Compare")
    with action_row[2]:
        if st.button("Start Ingest", key="home_ingest_footer", use_container_width=True):
            navigate_to("📥 Ingest")

    st.caption(
        "TalentFlow AI now opens with a landing shell that mirrors the requested dark/zinc editorial language while preserving the current Streamlit-based recruiter workflows."
    )


inject_global_styles()

# Sidebar navigation drives the app's recruiter workflows plus the new landing shell.
st.sidebar.title("✦ TalentFlow AI")
st.sidebar.caption("Nexus-style recruiter operating system")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["✦ Home", "📋 Candidates", "👤 Profile", "⚖️ Compare", "📌 Pipeline", "📥 Ingest"],
)
page = st.session_state.pop("page_override", page)
st.sidebar.markdown("---")


if page == "✦ Home":
    render_home_page()

elif page == "📋 Candidates":
    # Candidate list view: combine structured filters with semantic search.
    st.title("📋 All Candidates")

    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        skill_filter = st.text_input("Filter by skill", placeholder="e.g. python")
    with col2:
        location_filter = st.text_input("Filter by location", placeholder="e.g. Mumbai")
    with col3:
        exp_filter = st.number_input("Min experience (yrs)", min_value=0, value=0)
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🔍 Search", use_container_width=True)

    # Semantic search hits the Pinecone-backed endpoint instead of SQL filters.
    st.markdown("#### Natural language search")
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        nl_query = st.text_input(
            "Search by meaning",
            placeholder="e.g. backend engineer with startup experience",
            label_visibility="collapsed"
        )
    with col_btn:
        nl_search_btn = st.button("Search", use_container_width=True)

    # Prefer semantic search whenever the recruiter types a natural-language query.
    if nl_query:
        try:
            r = requests.get(f"{API_URL}/search", params={"q": nl_query, "limit": 20})
            candidates = r.json()
            st.caption(f"Semantic search results for: _{nl_query}_")
        except Exception:
            candidates = []
    else:
        candidates = fetch_candidates(
            skill=skill_filter or None,
            location=location_filter or None,
            min_exp=exp_filter if exp_filter > 0 else None,
        )

    st.markdown(f"**{len(candidates)} candidates found**")
    st.markdown("---")

    if not candidates:
        st.info("No candidates found. Try adjusting your filters or ingest some data first.")
    else:
        for candidate in candidates:
            with st.container():
                r1, r2, r3, r4 = st.columns([3, 2, 2, 1])

                with r1:
                    st.markdown(
                        f"**{source_badge(candidate.get('source', ''))} {candidate.get('name', 'Unknown')}**"
                    )
                    st.caption(f"{candidate.get('role', 'No role')} · {candidate.get('location', 'No location')}")

                with r2:
                    skills = candidate.get("skills") or []
                    if skills:
                        # Keep cards compact by showing only the first few skills.
                        st.markdown(" ".join([f"`{skill}`" for skill in skills[:4]]))
                    else:
                        st.caption("No skills listed")

                with r3:
                    exp = candidate.get("exp", 0) or 0
                    st.markdown(f"**{exp} yrs** experience")
                    # Search score only exists for semantic search responses.
                    if candidate.get("score"):
                        st.caption(f"Match score: {candidate.get('score'):.0%}")
                    stage = candidate.get("stage", "applied")
                    st.markdown(
                        f'<span style="background:{stage_color(stage)};color:white;'
                        f'padding:2px 8px;border-radius:10px;font-size:11px">{stage.upper()}</span>',
                        unsafe_allow_html=True,
                    )

                with r4:
                    if st.button("View", key=f"view_{candidate['id']}"):
                        # Session state lets the app jump directly to the selected profile.
                        st.session_state["selected_candidate"] = candidate["id"]
                        st.session_state["page_override"] = "👤 Profile"
                        st.rerun()

                st.markdown("---")

elif page == "👤 Profile":
    # Profile view: show one candidate in detail and allow stage updates.
    st.title("👤 Candidate Profile")

    all_candidates = fetch_candidates()
    if not all_candidates:
        st.info("No candidates yet. Ingest some data first.")
    else:
        names = {
            candidate["id"]: f"{candidate.get('name', 'Unknown')} ({candidate.get('source', '')})"
            for candidate in all_candidates
        }
        # Reuse the last selected candidate when the user navigates here from another page.
        default_id = st.session_state.get("selected_candidate", all_candidates[0]["id"])

        selected_id = st.selectbox(
            "Select candidate",
            options=list(names.keys()),
            format_func=lambda candidate_id: names[candidate_id],
            index=list(names.keys()).index(default_id) if default_id in names else 0,
        )

        candidate = fetch_candidate(selected_id) or next(
            (item for item in all_candidates if item["id"] == selected_id),
            None,
        )

        if candidate:
            st.markdown("---")
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(
                    f"## {source_badge(candidate.get('source', ''))} {candidate.get('name', 'Unknown')}"
                )
                st.markdown(f"**Role:** {candidate.get('role', 'Not specified')}")
                st.markdown(f"**Location:** {candidate.get('location', 'Not specified')}")
                st.markdown(f"**Experience:** {candidate.get('exp', 0)} years")
                st.markdown(f"**Email:** {candidate.get('email', 'Not available')}")
                st.markdown(f"**Source:** `{candidate.get('source', 'unknown')}`")

                st.markdown("### Skills")
                skills = candidate.get("skills") or []
                if skills:
                    st.markdown(" ".join([f"`{skill}`" for skill in skills]))
                else:
                    st.info("No skills extracted for this candidate.")

                metadata = candidate.get("source_metadata") or {}
                if metadata:
                    # Source-specific attributes are shown separately from the common profile fields.
                    st.markdown("### Source Metadata")
                    st.json(metadata)

            with col2:
                st.markdown("### Pipeline stage")
                current_stage = candidate.get("stage", "applied")
                new_stage = st.selectbox(
                    "Update stage",
                    options=STAGES,
                    index=STAGES.index(current_stage) if current_stage in STAGES else 0,
                )
                if st.button("💾 Save stage", use_container_width=True):
                    if update_stage(candidate["id"], new_stage):
                        st.success(f"Stage updated to {new_stage}")
                        st.rerun()
                    else:
                        st.error("Failed to update stage")

                st.markdown("---")
                st.markdown("### Source")
                st.markdown(
                    f"{source_badge(candidate.get('source', ''))} **{candidate.get('source', '').upper()}**"
                )

elif page == "⚖️ Compare":
    # Side-by-side comparison view for shortlist decisions.
    st.title("⚖️ Compare Candidates")

    all_candidates = fetch_candidates()
    if len(all_candidates) < 2:
        st.info("You need at least 2 candidates to compare.")
    else:
        names = {candidate["id"]: candidate.get("name", "Unknown") for candidate in all_candidates}

        col1, col2 = st.columns(2)
        with col1:
            id_a = st.selectbox(
                "Candidate A",
                options=list(names.keys()),
                format_func=lambda candidate_id: names[candidate_id],
                key="compare_a",
            )
        with col2:
            remaining = {key: val for key, val in names.items() if key != id_a}
            id_b = st.selectbox(
                "Candidate B",
                options=list(remaining.keys()),
                format_func=lambda candidate_id: remaining[candidate_id],
                key="compare_b",
            )

        candidate_a = next((c for c in all_candidates if c["id"] == id_a), None)
        candidate_b = next((c for c in all_candidates if c["id"] == id_b), None)

        if candidate_a and candidate_b:
            st.markdown("---")
            c1, c2 = st.columns(2)

            def render_profile(column, item):
                """Render one compact candidate summary inside a comparison column."""
                with column:
                    st.markdown(f"### {source_badge(item.get('source', ''))} {item.get('name', 'Unknown')}")
                    st.markdown(f"**Role:** {item.get('role', '—')}")
                    st.markdown(f"**Location:** {item.get('location', '—')}")
                    st.markdown(f"**Experience:** {item.get('exp', 0)} yrs")
                    st.markdown(f"**Email:** {item.get('email', '—')}")
                    stage = item.get("stage", "applied")
                    st.markdown(
                        f'<span style="background:{stage_color(stage)};color:white;'
                        f'padding:2px 8px;border-radius:10px;font-size:11px">{stage.upper()}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("**Skills:**")
                    skills = item.get("skills") or []
                    if skills:
                        st.markdown(" ".join([f"`{skill}`" for skill in skills]))
                    else:
                        st.caption("No skills listed")

            render_profile(c1, candidate_a)
            render_profile(c2, candidate_b)

            st.markdown("---")
            st.markdown("### Skill overlap")
            # Set math makes overlap/differences easy to explain visually.
            skills_a = set(candidate_a.get("skills") or [])
            skills_b = set(candidate_b.get("skills") or [])
            common = skills_a & skills_b
            only_a = skills_a - skills_b
            only_b = skills_b - skills_a

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Only {candidate_a.get('name', 'A').split()[0]} has:**")
                st.markdown(" ".join([f"`{skill}`" for skill in only_a]) if only_a else "_none_")
            with col2:
                st.markdown("**Both have:**")
                st.markdown(" ".join([f"`{skill}`" for skill in common]) if common else "_none_")
            with col3:
                st.markdown(f"**Only {candidate_b.get('name', 'B').split()[0]} has:**")
                st.markdown(" ".join([f"`{skill}`" for skill in only_b]) if only_b else "_none_")

elif page == "📌 Pipeline":
    # Kanban-style view of the hiring funnel.
    st.title("📌 Recruitment Pipeline")

    all_candidates = fetch_candidates()
    if not all_candidates:
        st.info("No candidates yet.")
    else:
        columns = st.columns(len(STAGES))
        for index, stage in enumerate(STAGES):
            with columns[index]:
                # Group candidates client-side because the API currently returns a flat list.
                stage_candidates = [candidate for candidate in all_candidates if candidate.get("stage") == stage]
                st.markdown(
                    f'<div style="background:{stage_color(stage)};color:white;'
                    f'padding:6px 10px;border-radius:8px;text-align:center;'
                    f'font-size:12px;font-weight:500;margin-bottom:10px">'
                    f'{stage.upper()} ({len(stage_candidates)})</div>',
                    unsafe_allow_html=True,
                )
                for candidate in stage_candidates:
                    with st.container():
                        st.markdown(
                            f'<div style="border:0.5px solid #ccc;border-radius:8px;'
                            f'padding:8px 10px;margin-bottom:6px;font-size:12px">'
                            f'<b>{source_badge(candidate.get("source", ""))} {candidate.get("name", "Unknown")}</b><br>'
                            f'<span style="color:grey">{candidate.get("role", "")}</span></div>',
                            unsafe_allow_html=True,
                        )
                        next_stages = [value for value in STAGES if value != stage]
                        new_stage = st.selectbox(
                            "Move to",
                            options=next_stages,
                            key=f"kanban_{candidate['id']}",
                            label_visibility="collapsed",
                        )
                        if st.button("Move", key=f"move_{candidate['id']}", use_container_width=True):
                            update_stage(candidate["id"], new_stage)
                            st.rerun()

elif page == "📥 Ingest":
    # Ingestion page exposes the three backend-driven import workflows.
    st.title("📥 Ingest Candidates")

    tab1, tab2, tab3 = st.tabs(["📄 Resume Upload", "🏢 BambooHR", "📧 Gmail"])

    with tab1:
        st.markdown("### Upload a resume PDF")
        uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])
        if uploaded and st.button("Parse & Ingest", use_container_width=True):
            with st.spinner("Parsing resume with LlamaExtract..."):
                # The backend expects multipart form upload under the `file` field.
                files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                response = requests.post(f"{API_URL}/ingest/resume", files=files, timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    st.success(f"✅ Ingested: **{data.get('name')}**")
                    st.markdown(f"**Skills found:** {', '.join(data.get('skills', []))}")
                    st.json(data)
                else:
                    st.error(f"Failed: {response.text}")

    with tab2:
        st.markdown("### Sync from BambooHR")
        st.caption("Fetches all active employees from your BambooHR account")
        if st.button("🔄 Sync BambooHR", use_container_width=True):
            with st.spinner("Connecting to BambooHR..."):
                # This delegates all paging/auth/upsert logic to the backend sync route.
                response = requests.post(f"{API_URL}/integrations/bamboohr/sync", timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    inserted = data.get("inserted", "?")
                    updated = data.get("updated", "?")
                    st.success(f"✅ Done! {inserted} inserted, {updated} updated")
                else:
                    st.error(f"Failed: {response.text}")

    with tab3:
        st.markdown("### Sync from Gmail")
        st.caption("Fetches last 20 emails with PDF attachments from your inbox")
        if st.button("📧 Sync Gmail", use_container_width=True):
            with st.spinner("Connecting to Gmail..."):
                # Gmail sync can take longer because it downloads attachments and parses PDFs.
                response = requests.post(f"{API_URL}/ingest/gmail", timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    st.success(
                        f"✅ Done! {data.get('inserted')} inserted, {data.get('updated')} updated"
                    )
                else:
                    st.error(f"Failed: {response.text}")

