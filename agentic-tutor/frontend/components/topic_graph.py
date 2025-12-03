# frontend/components/topic_graph.py
import streamlit as st
import graphviz
import requests
import json

def render_topic_graph():
    BASE_URL = "http://127.0.0.1:5010"
    
    try:
        # Fetch actual topic graph from backend
        response = requests.get(f"{BASE_URL}/api/topics/graph", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            topics = data.get("topics", {})
            edges = data.get("edges", [])
            mastery_data = data.get("mastery_map", {})
        else:
            # Fallback to static if API fails
            topics, edges, mastery_data = get_static_fallback()
            
    except Exception:
        topics, edges, mastery_data = get_static_fallback()
    
    # Create graph with real data
    dot = graphviz.Digraph(comment="Dynamic Topic Graph")
    dot.attr(rankdir="TB", size="10")
    
    for category, subs in topics.items():
        with dot.subgraph(name=f"cluster_{category}") as c:
            c.attr(label=category, style="dashed")
            for topic in subs:
                # Use REAL mastery data
                mastery = mastery_data.get(topic, {}).get("mastery_level", 0.0)
                color = get_mastery_color(mastery)
                c.node(topic, style="filled", fillcolor=color)
    
    # Add REAL edges
    for edge in edges:
        dot.edge(edge["from"], edge["to"], label=edge.get("type", ""))
    
    st.graphviz_chart(dot)

def get_static_fallback():
    """Fallback static data"""
    return {
        "Foundations": ["Vectors", "Vector Spaces", "Linear Independence"],
        "Transformations": ["Linear Maps", "Matrix Representation", "Change of Basis"],
        "Spectral Theory": ["Eigenvalues", "Eigenvectors", "Diagonalization"],
        "Decompositions": ["LU", "QR", "SVD", "Jordan Form"],
        "Applications": ["Least Squares", "PCA", "Markov Chains"]
    }, [
        {"from": "Vector Spaces", "to": "Linear Transformations"},
    ],

def get_mastery_color(mastery):
    if mastery > 0.8:
        return "green"
    elif mastery > 0.5:
        return "orange"
    else:
        return "red"