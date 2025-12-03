# backend/app/routers/topic_router.py
from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import Dict, Any
import asyncio

from backend.app.database.session import get_session
from backend.app.core.rag.tavily_client import TavilySearch
from backend.app.database.models import StudentProfile

router = APIRouter()

@router.get("/api/topics/graph")
async def get_topic_graph(
    student_id: str = "default",
    session: Session = Depends(get_session)
):
    """Get dynamic topic graph with mastery levels"""
    
    # 1. Get student's mastery
    profile = session.get(StudentProfile, student_id)
    mastery_map = profile.mastery_map if profile else {}
    
    # 2. Get base curriculum topics
    topics = get_curriculum_topics()
    
    # 3. Get emerging topics (async)
    emerging_topics = await get_emerging_topics()
    
    # 4. Merge topics
    all_topics = {**topics, "Emerging": emerging_topics}
    
    # 5. Get prerequisite edges
    edges = get_topic_edges(all_topics)
    
    return {
        "topics": all_topics,
        "edges": edges,
        "mastery_map": mastery_map,
        "emerging_topics": emerging_topics
    }

async def get_emerging_topics():
    """Use Tavily to find trending Linear Algebra topics"""
    try:
        # Search for recent developments
        query = "linear algebra recent developments 2024 applications machine learning"
        results = TavilySearch.search(query, max_results=5)
        
        emerging = []
        for result in results:
            # Extract topics from search results
            # Simple keyword extraction (in reality, use NLP)
            if "spectral" in result.lower():
                emerging.append("Spectral Graph Theory")
            if "tensor" in result.lower():
                emerging.append("Tensor Decomposition")
            if "quantum" in result.lower():
                emerging.append("Quantum Linear Algebra")
                
        return list(set(emerging))[:3]  # Top 3 unique topics
        
    except Exception:
        return ["Graph Neural Networks", "Tensor Methods"]

def get_curriculum_topics():
    """Read from curriculum database or file"""
    return {
        "Foundations": ["Vectors", "Vector Spaces", "Linear Independence"],
        "Transformations": ["Linear Maps", "Matrix Representation", "Change of Basis"],
        "Spectral Theory": ["Eigenvalues", "Eigenvectors", "Diagonalization"],
        "Decompositions": ["LU", "QR", "SVD", "Jordan Form"],
        "Applications": ["Least Squares", "PCA", "Markov Chains"]
    }

def get_topic_edges(topics: Dict[str, Any]):
    """Define prerequisite relationships"""
    edges = [
        {"from": "Vectors", "to": "Vector Spaces", "type": "prerequisite"},
        {"from": "Vector Spaces", "to": "Linear Maps", "type": "prerequisite"},
        {"from": "Linear Maps", "to": "Eigenvalues", "type": "prerequisite"},
        {"from": "Eigenvalues", "to": "SVD", "type": "prerequisite"},
        {"from": "SVD", "to": "PCA", "type": "application"},
    ]
    return edges