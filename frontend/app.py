import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"]

st.set_page_config(page_title="Recruitment Platform", page_icon="👥", layout="wide")


# Sidebar navigation
st.sidebar.title("👥 Recruitment Platform")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["📋 Candidates", "👤 Profile", "⚖️ Compare", "📌 Pipeline", "📥 Ingest"],
)
page = st.session_state.pop("page_override", page)
st.sidebar.markdown("---")


def fetch_candidates(skill=None, location=None, min_exp=None):
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
        return []


def fetch_candidate(candidate_id):
    try:
        response = requests.get(f"{API_URL}/candidates/{candidate_id}", timeout=20)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def update_stage(candidate_id, stage):
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
    colors = {
        "resume": "🔵",
        "bamboohr": "🟢",
        "gmail": "🔴",
        "linkedin": "🟡",
    }
    return colors.get(source, "⚪")


def stage_color(stage):
    colors = {
        "applied": "#888780",
        "screening": "#185FA5",
        "interview": "#854F0B",
        "offer": "#534AB7",
        "hired": "#0F6E56",
        "rejected": "#A32D2D",
    }
    return colors.get(stage, "#888780")


if page == "📋 Candidates":
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
                        st.markdown(" ".join([f"`{skill}`" for skill in skills[:4]]))
                    else:
                        st.caption("No skills listed")

                with r3:
                    exp = candidate.get("exp", 0) or 0
                    st.markdown(f"**{exp} yrs** experience")
                    stage = candidate.get("stage", "applied")
                    st.markdown(
                        f'<span style="background:{stage_color(stage)};color:white;'
                        f'padding:2px 8px;border-radius:10px;font-size:11px">{stage.upper()}</span>',
                        unsafe_allow_html=True,
                    )

                with r4:
                    if st.button("View", key=f"view_{candidate['id']}"):
                        st.session_state["selected_candidate"] = candidate["id"]
                        st.session_state["page_override"] = "👤 Profile"
                        st.rerun()

                st.markdown("---")

elif page == "👤 Profile":
    st.title("👤 Candidate Profile")

    all_candidates = fetch_candidates()
    if not all_candidates:
        st.info("No candidates yet. Ingest some data first.")
    else:
        names = {
            candidate["id"]: f"{candidate.get('name', 'Unknown')} ({candidate.get('source', '')})"
            for candidate in all_candidates
        }
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
    st.title("📌 Recruitment Pipeline")

    all_candidates = fetch_candidates()
    if not all_candidates:
        st.info("No candidates yet.")
    else:
        columns = st.columns(len(STAGES))
        for index, stage in enumerate(STAGES):
            with columns[index]:
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
    st.title("📥 Ingest Candidates")

    tab1, tab2, tab3 = st.tabs(["📄 Resume Upload", "🏢 BambooHR", "📧 Gmail"])

    with tab1:
        st.markdown("### Upload a resume PDF")
        uploaded = st.file_uploader("Choose a PDF file", type=["pdf"])
        if uploaded and st.button("Parse & Ingest", use_container_width=True):
            with st.spinner("Parsing resume with LlamaExtract..."):
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
                response = requests.post(f"{API_URL}/ingest/gmail", timeout=120)
                if response.status_code == 200:
                    data = response.json()
                    st.success(
                        f"✅ Done! {data.get('inserted')} inserted, {data.get('updated')} updated"
                    )
                else:
                    st.error(f"Failed: {response.text}")

