# frontend/components/misconception_log.py
import streamlit as st

def render_misconceptions(misconceptions: list):
    st.subheader("Detected Misconceptions")
    if not misconceptions:
        st.success("No major misconceptions detected yet!")
        return

    for i, m in enumerate(misconceptions[-5:]):  # Show last 5
        level = "🔴" if "confuses" in m.lower() or "forgets" in m.lower() else "🟡"
        st.markdown(f"{level} **{m}**")
    
    if len(misconceptions) > 5:
        st.caption(f"Total tracked: {len(misconceptions)} misconceptions")