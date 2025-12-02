# frontend/components/topic_graph.py
import streamlit as st
import graphviz

def render_topic_graph():
    dot = graphviz.Digraph(comment="Linear Algebra Topic Graph")
    dot.attr(rankdir="TB", size="10")

    topics = {
        "Vectors": ["Vector Spaces", "Subspaces"],
        "Linear Transformations": ["Kernel", "Image", "Matrix Representation"],
        "Eigen": ["Eigenvalues & Eigenvectors", "Diagonalization", "Spectral Theorem"],
        "Decomp": ["LU", "QR", "SVD", "Jordan Form"],
        "Inner": ["Inner Product Spaces", "Orthogonality", "Gram-Schmidt"]
    }

    for category, subs in topics.items():
        with dot.subgraph(name=f"cluster_{category}") as c:
            c.attr(label=category, style="dashed")
            for t in subs:
                mastery = 0.7  # from DB later
                color = "green" if mastery > 0.8 else "orange" if mastery > 0.5 else "red"
                c.node(t, style="filled", fillcolor=color)
    
    dot.edge("Vector Spaces", "Linear Transformations")
    dot.edge("Linear Transformations", "Eigenvalues & Eigenvectors")
    dot.edge("Eigenvalues & Eigenvectors", "Spectral Theorem")
    dot.edge("Matrix Representation", "LU")
    dot.edge("LU", "SVD")

    st.graphviz_chart(dot)