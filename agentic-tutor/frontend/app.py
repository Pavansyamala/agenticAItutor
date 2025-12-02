# frontend/app.py
import streamlit as st
from pathlib import Path

import os, sys
print("CWD:", os.getcwd())
print("PATH:", sys.path)

# ABSOLUTE PATH OF CURRENT FILE
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# PARENT: agentic-tutor/
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

print(">> Added to PATH:", PARENT_DIR)
print(">> sys.path:", sys.path[:3])


# Now imports work perfectly
from frontend.utils.api_client import APIClient  
from components.topic_graph import render_topic_graph
from components.progress_radar import render_radar
from components.misconception_log import render_misconceptions
from components.session_timeline import render_timeline

# Page config
st.set_page_config(page_title="Adaptive Linear Algebra Tutor", layout="wide", initial_sidebar_state="expanded")

# Title with your names and IDs — exactly as in your document
st.title("Adaptive Agentic Teaching Assistant for Linear Algebra")
st.markdown("""  
**Course: Generative and Agentic AI (DS246) — Capstone Project**
""")

API = APIClient()

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def export_profile_pdf(profile, filename="student_profile.pdf"):
    pdf_path = f"/tmp/{filename}"
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(50, 750, "Student Profile Report")
    y = 720

    for k,v in profile.items():
        if k == "mastery_map":
            c.drawString(50, y, "Mastery Map:")
            y -= 20
            for topic,score in v.items():
                c.drawString(70, y, f"{topic}: {score:.2f}")
                y -= 15
        elif k == "misconceptions":
            c.drawString(50, y, "Misconceptions:")
            y -= 20
            for m in v:
                c.drawString(70, y, f"- {m}")
                y -= 15
        else:
            c.drawString(50, y, f"{k}: {v}")
            y -= 20

    c.save()
    return pdf_path


# Sidebar
with st.sidebar:
    st.header("Student Session")
    student_id = st.text_input("Student ID", value="26738", help="Enter your ID")
    topic = st.selectbox("Select Topic", [
        "Vector Spaces", "Linear Transformations", "Eigenvalues & Eigenvectors",
        "Matrix Decompositions", "Inner Product Spaces", "Spectral Theorem"
    ], index=2)

    if st.button("Start New Session", type="primary"):
        with st.spinner("Starting adaptive session..."):
            resp = API.start_session(student_id, topic)
            if "thread_id" in resp:
                st.session_state.thread_id = resp["thread_id"]
                st.session_state.student_id = student_id
                st.success(f"Session started: `{resp['thread_id'][:8]}`")
                st.rerun()
            else:
                st.error("Backend not ready. Is uvicorn running?")

    if st.session_state.get("thread_id"):
        st.info(f"Active Session: `{st.session_state.thread_id[:8]}`")

    # Button in sidebar
    if st.sidebar.button("Export Student Profile (PDF)"):
        profile = APIClient().get_profile(student_id)
        path = export_profile_pdf(profile)
        with open(path, "rb") as f:
            st.sidebar.download_button(
                label="Download Profile PDF",
                data=f,
                file_name="student_profile.pdf",
                mime="application/pdf"
            )

# Main content
if "thread_id" not in st.session_state:
    st.info("Start a session from the sidebar to begin learning.")
    st.stop()

thread_id = st.session_state.thread_id
state = API.get_session_state(thread_id)

import time

def animated_transition(text="Loading next step...", delay=0.4):
    ph = st.empty()
    for dots in ["", ".", "..", "..."]:
        ph.markdown(f"### {text}{dots}")
        time.sleep(delay)
    ph.empty()


col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Current Lesson")
    if state.get("lesson_plan"):
        for step in state.get("lesson_plan", []):
            # Case 1 — step is a list (malformed)
            if isinstance(step, list):
                st.warning("⚠️ Tutor returned a malformed lesson step (list instead of dict). Showing raw data.")
                st.json(step)
                continue

            # Case 2 — step is a simple string
            elif isinstance(step, str):
                st.markdown("### Lesson Content")
                st.markdown(step)
                continue

            # Case 3 — VALID dict step (normal execution)
            else:
                with st.expander(
                    f"Step {step.get('step', '')}: {step.get('title', 'Lesson Step')}",
                    expanded=True
                ):
                    st.markdown(step.get("content", ""))



    st.subheader("Evaluation Questions")
    questions = state.get("questions", [])
    answers = st.session_state.get("answers", {})

    with st.form("answers_form"):
        for q in questions:
            qid = q["qid"]
            with st.expander(f"Question {qid} — {q['type'].title()}", expanded=True):
                st.markdown(q["prompt"])
                answers[qid] = st.text_area("Your answer", value=answers.get(qid, ""), key=f"ans_{qid}", height=120)
        
        submitted = st.form_submit_button("Submit Answers for SymPy + RAG Grading")
        if submitted:
            animated_transition("Updating lesson state")
            payload = [{"qid": qid, "answer": ans} for qid, ans in answers.items()]
            with st.spinner("Grading with SymPy verification..."):
                result = API.submit_answers(thread_id, payload)
                st.session_state.last_result = result
                st.success("Graded! See results below.")
                st.rerun()

with col2:
    st.subheader("Mastery Profile")
    profile = API.get_profile(student_id)
    render_radar(profile.get("mastery_map", {}))
    render_misconceptions(profile.get("misconceptions", []))

    if state.get("monitor_decision"):
        action = state["monitor_decision"].get("remediation_plan", {}).get("action", "advance")
        color = {"remedial": "red", "practice": "orange", "advance": "green"}.get(action, "gray")
        st.markdown(f"**Next Action:** <span style='color:{color};font-size:18px'>{action.upper()}</span>", unsafe_allow_html=True)
        dec = state["monitor_decision"]
        plan = dec.get("remediation_plan")

        st.subheader("Remediation Path")

        if plan:
            color = {
                "remedial": "red",
                "practice": "orange",
                "review": "blue",
                "accelerate": "green"
            }.get(plan["action"], "gray")

            st.markdown(
                f"""
                <div style="padding:10px;border-radius:6px;
                    border-left:6px solid {color};
                    background-color:#f8f9fa">
                    <b>Action:</b> {plan["action"].upper()}<br>
                    <b>Mode:</b> {plan["recommended_tutor_mode"].title()}<br>
                    <hr>
                    {"<br>".join(f"• {step}" for step in plan["steps"])}
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.success("No remediation needed. Student may advance.")


        # -----------------------------------------
        # SHOW GRADING RESULTS (if available)
        # -----------------------------------------
        if "last_result" in st.session_state:
            print("Rendering last result...")
            st.subheader("Evaluation Results")

            res = st.session_state.last_result

            # Show overall score
            score = res.get("overall_score", None)
            print(res)
            print(score)
            if score is not None:
                st.metric("Overall Score", f"{score*100:.1f}%")

            # Show per-question grading tables
            grading = res.get("grading", {})
            if grading:
                rows = []
                for qid, info in grading.items():
                    rows.append({
                        "QID": qid,
                        "Score": info.get("score"),
                        "Max": info.get("max")
                    })
                st.table(rows)

            # Show misconceptions
            misconceptions = res.get("misconceptions", [])
            if misconceptions:
                st.subheader("Detected Misconceptions")
                for m in misconceptions:
                    st.markdown(f"🔎 **{m}**")

            # Show feedback summary
            feedback = res.get("feedback", "")
            if feedback:
                st.info(feedback)


# Bottom tabs
st.divider()
tab1, tab2, tab3 = st.tabs(["Topic Prerequisite Graph", "Session Timeline", "Raw State"])

import plotly.express as px

with tab1:
    import pandas as pd
    st.subheader("Mastery Heatmap")
    mastery_map = profile.get("mastery_map", {})
    df_heat = pd.DataFrame({
        "Topic": list(mastery_map.keys()),
        "Mastery": list(mastery_map.values())
    })

    fig = px.density_heatmap(
        df_heat,
        x="Topic",
        y="Mastery",
        z="Mastery",
        color_continuous_scale="RdYlGn",
        height=320
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    render_topic_graph()

with tab2:
    render_timeline(thread_id)

with tab3:
    st.json(state, expanded=False)