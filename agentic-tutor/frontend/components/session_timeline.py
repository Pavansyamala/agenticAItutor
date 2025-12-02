# frontend/components/session_timeline.py
import streamlit as st
import requests
from datetime import datetime
import pandas as pd

def fetch_events(student_id: str = None, thread_id: str = None):
    """
    Fetch real events from your backend Event table
    We'll add a new endpoint: GET /api/events
    """
    try:
        params = {}
        if student_id:
            params["student_id"] = student_id
        if thread_id:
            params["thread_id"] = thread_id

        resp = requests.get("http://127.0.0.1:5000/api/events", params=params, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("events", [])
    except:
        pass
    return []

def render_timeline(thread_id: str):
    st.subheader("Session Timeline (Live from Database)")

    # Get thread_id from session state
    student_id = st.session_state.get("student_id")

    events = fetch_events(student_id=student_id, thread_id=thread_id)

    if not events:
        st.info("No events recorded yet. Activity will appear here in real-time.")
        return

    # Parse and format
    rows = []
    for e in events:
        time = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
        payload = e.get("payload", {})

        event_text = e["event_type"].replace("_", " ").title()
        detail = ""

        if e["event_type"] == "session_started":
            detail = f"Topic: {payload.get('topic')}"
        elif e["event_type"] == "lesson_delivered":
            detail = f"Steps: {len(payload.get('plan', []))}"
        elif e["event_type"] == "questions_generated":
            detail = f"{len(payload.get('questions', []))} questions • {', '.join(q['type'] for q in payload.get('questions', [])[:3])}"
        elif e["event_type"] == "answers_graded":
            score = payload.get("overall_score", 0)
            sympy = sum(1 for q in payload.get("grading", {}).values() if q.get("sympy_used"))
            detail = f"Score: {score:.1%} • SymPy verified: {sympy}/{len(payload.get('grading', {}))}"
        elif e["event_type"] == "monitor_decision":
            action = payload.get("remediation_plan", {}).get("action", "advance")
            detail = f"→ {action.upper()}"

        rows.append({
            "Time": time.strftime("%H:%M:%S"),
            "Event": event_text,
            "Details": detail or "—"
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Export
    csv = df.to_csv(index=False)
    st.download_button(
        label="Export Session Log (CSV)",
        data=csv,
        file_name=f"linear_algebra_session_{thread_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )