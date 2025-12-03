# frontend/app.py
import streamlit as st
from pathlib import Path
import sys
import os
import time
import json
from io import BytesIO

# Add project root to path
CURRENT_DIR = Path(__file__).parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.utils.api_client import APIClient
from components.topic_graph import render_topic_graph
from components.progress_radar import render_radar
from components.misconception_log import render_misconceptions
from components.session_timeline import render_timeline

st.set_page_config(page_title="Adaptive Linear Algebra Tutor", layout="wide", initial_sidebar_state="expanded")
st.title("Adaptive Agentic Teaching Assistant")
st.markdown("**DS246 — Generative & Agentic AI | IISc Bangalore**")

API = APIClient()

# ========================
# Session State Init
# ========================
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "student_id" not in st.session_state:
    st.session_state.student_id = "26738"
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# ========================
# Sidebar
# ========================
with st.sidebar:
    st.header("Student Control Panel")
    student_id = st.text_input("Student ID", value=st.session_state.student_id)
    topic = st.selectbox("Select Topic", [
        "Vector Spaces",
        "Linear Transformations",
        "Eigenvalues & Eigenvectors",
        "Matrix Decompositions",
        "Inner Product Spaces",
        "Spectral Theorem"
    ])

    if st.button("Start New Session", type="primary", use_container_width=True):
        st.session_state.student_id = student_id
        with st.spinner("Initializing adaptive session..."):
            resp = API.start_session(student_id, topic)
            if resp and resp.get("thread_id"):
                st.session_state.thread_id = resp["thread_id"]
                st.session_state.answers = {}
                st.session_state.last_result = None
                st.success(f"Session Active: `{resp['thread_id'][:10]}`")
                st.rerun()
            else:
                st.error("Failed to start session. Is backend running?")

    if st.session_state.thread_id:
        st.info(f"**Active Session**\n`{st.session_state.thread_id[:12]}...`")

    if st.button("Export Profile PDF", disabled=not st.session_state.thread_id):
        profile = API.get_profile(student_id)
        if profile and "mastery_map" in profile:
            pdf = export_profile_pdf(profile)
            st.download_button(
                "Download Profile PDF",
                data=pdf,
                file_name=f"profile_{student_id}_{topic.replace(' ', '_').lower()}.pdf",
                mime="application/pdf"
            )

# ========================
# Main App Logic
# ========================
if not st.session_state.thread_id:
    st.info("← Start a session from the sidebar to begin learning.")
    st.stop()

thread_id = st.session_state.thread_id
state = API.get_session_state(thread_id) or {}

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Current Lesson Plan")

    lesson_plan = state.get("lesson_plan")
    if lesson_plan and isinstance(lesson_plan, list):
        for i, step in enumerate(lesson_plan):
            with st.expander(f"Step {i+1}: {step.get('title', 'Untitled')}", expanded=True):
                st.markdown(step.get("content", "No content provided."))
    else:
        st.info("Lesson will appear here once generated...")

    # === QUIZ SECTION ===
    questions = state.get("questions", [])
    grading_result = state.get("grading_result")

    if not questions:
        st.warning("No questions yet.")
        if st.button("Generate Quiz Questions", type="secondary", use_container_width=True):
            with st.spinner("Generating adaptive questions..."):
                # This triggers the evaluation cycle with empty answers → generates questions
                result = API.submit_answers(thread_id, [])
                if result and result.get("questions"):
                    st.success("Questions generated!")
                    st.rerun()
                else:
                    st.error("Failed to generate questions.")
    else:
        st.success(f"{len(questions)} Question(s) Ready")

        with st.form("answer_form"):
            for q in questions:
                qid = q["qid"]
                prompt = q["prompt"]
                st.markdown(f"**Q{qid}:** {prompt}")
                st.session_state.answers[qid] = st.text_area(
                    "Your Answer",
                    value=st.session_state.answers.get(qid, ""),
                    key=f"input_{qid}_{thread_id}",
                    height=120,
                    label_visibility="collapsed"
                )
                st.markdown("---")

            if st.form_submit_button("Submit Answers for Grading", type="primary", use_container_width=True):
                payload = [
                    {"qid": qid, "answer": ans.strip()}
                    for qid, ans in st.session_state.answers.items()
                    if ans.strip()
                ]
                with st.spinner("Grading your answers..."):
                    result = API.submit_answers(thread_id, payload)
                    st.session_state.last_result = result
                    st.success("Grading complete!")
                    st.rerun()

with col2:
    st.subheader("Mastery Profile")
    profile = API.get_profile(st.session_state.student_id) or {}
    render_radar(profile.get("mastery_map", {}))
    render_misconceptions(profile.get("misconceptions", []))

    # Monitor Decision
    decision = state.get("monitor_decision") or {}
    allow_advance = decision.get("allow_advance", False)
    plan = decision.get("remediation_plan", {})

    if allow_advance:
        st.success("**Ready to Advance!**")
    else:
        action = plan.get("action", "review") if plan else "hold"
        color = {"remedial": "red", "practice": "orange", "review": "blue"}.get(action, "gray")
        st.markdown(f"**Next Step:** <span style='color:{color}'>{action.upper()}</span>", unsafe_allow_html=True)

        if plan and plan.get("steps"):
            st.markdown("**Recommended Path:**")
            for step in plan["steps"]:
                st.markdown(f"• {step}")

    # Show latest grading
    if st.session_state.last_result:
        res = st.session_state.last_result
        score = res.get("overall_score") or (res.get("grading") or {}).get("overall_score")
        if score is not None:
            st.metric("Latest Score", f"{float(score):.2%}")

        if res.get("misconceptions"):
            st.error("Misconceptions Detected:")
            for m in res["misconceptions"]:
                st.markdown(f"• {m}")

# ========================
# Bottom Tabs
# ========================
st.divider()
tab1, tab2, tab3 = st.tabs(["Prerequisite Graph", "Session Timeline", "Debug State"])

with tab1:
    render_topic_graph()

with tab2:
    render_timeline(thread_id)

with tab3:
    st.json(state, expanded=False)


# ========================
# PDF Export Helper
# ========================
def export_profile_pdf(profile: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        return json.dumps(profile, indent=2).encode()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Student Mastery Report")
    c.setFont("Helvetica", 12)
    y = height - 100

    for key, value in profile.items():
        if key == "mastery_map" and isinstance(value, dict):
            c.drawString(50, y, "Mastery Levels:")
            y -= 20
            for topic, score in value.items():
                c.drawString(70, y, f"• {topic}: {score:.3f}")
                y -= 18
        y -= 10

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()