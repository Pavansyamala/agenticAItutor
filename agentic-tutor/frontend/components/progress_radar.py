# frontend/components/progress_radar.py
import streamlit as st
import plotly.graph_objects as go

def render_radar(mastery_map: dict):
    if not mastery_map:
        st.info("Mastery data will appear after first evaluation.")
        return

    topics = list(mastery_map.keys())
    values = [mastery_map.get(t, 0.0) for t in topics]

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=topics,
        fill='toself',
        line_color='deepskyblue',
        fillcolor='rgba(135, 206, 250, 0.3)'
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
        title="Mastery Radar Chart",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)