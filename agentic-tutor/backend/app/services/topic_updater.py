# backend/app/services/topic_updater.py
import schedule
import time
import asyncio
from datetime import datetime
from typing import List
import arxiv

from backend.app.database.session import get_session
from backend.app.database.models import TopicGraph
from backend.app.core.rag.tavily_client import TavilySearch

class TopicUpdater:
    def __init__(self):
        self.topic_graph = {}
        
    async def weekly_update(self):
        """Run weekly to update topic graph"""
        print(f"[{datetime.now()}] Starting weekly topic update...")
        
        # 1. Search for trending topics
        trending = await self.get_trending_topics()
        
        # 2. Get recent papers
        papers = self.get_recent_papers()
        
        # 3. Cluster and extract new topics
        new_topics = self.extract_new_topics(trending, papers)
        
        # 4. Update database
        self.update_topic_graph(new_topics)
        
        print(f"[{datetime.now()}] Added {len(new_topics)} new topics")
        
    async def get_trending_topics(self) -> List[str]:
        """Use Tavily to find what's trending"""
        queries = [
            "linear algebra machine learning recently",
            "matrix decomposition applications",
            "eigenvalue computation recent advances"
        ]
        
        all_topics = []
        for query in queries:
            try:
                results = TavilySearch.search(query, max_results=3)
                for result in results:
                    # Simple extraction - in reality use NLP
                    if "graph" in result.lower() and "neural" in result.lower():
                        all_topics.append("Graph Neural Networks")
                    if "quantum" in result.lower():
                        all_topics.append("Quantum Linear Algebra")
                    if "tensor" in result.lower():
                        all_topics.append("Tensor Methods")
            except:
                continue
                
        return list(set(all_topics))
    
    def get_recent_papers(self):
        """Fetch recent arXiv papers"""
        client = arxiv.Client()
        search = arxiv.Search(
            query="cat:math.NA OR cat:cs.LG",
            max_results=10,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        return list(client.results(search))
    
    def extract_new_topics(self, trending: List[str], papers: List) -> List[str]:
        """Combine sources to find genuinely new topics"""
        # Simple heuristic
        new_topics = set(trending)
        
        for paper in papers[:5]:  # Check most recent papers
            if any(keyword in paper.title.lower() for keyword in ["spectral", "graph", "neural"]):
                new_topics.add("Spectral Graph Neural Networks")
            if "tensor" in paper.title.lower():
                new_topics.add("Tensor Decomposition Methods")
                
        return list(new_topics)
    
    def update_topic_graph(self, new_topics: List[str]):
        """Store new topics in database"""
        with get_session() as session:
            for topic in new_topics:
                existing = session.query(TopicGraph).filter(
                    TopicGraph.name == topic
                ).first()
                
                if not existing:
                    new_node = TopicGraph(
                        name=topic,
                        category="Emerging",
                        difficulty=0.7,
                        created_at=datetime.utcnow(),
                        source="auto_generated"
                    )
                    session.add(new_node)
            
            session.commit()

# Schedule weekly updates
updater = TopicUpdater()

# In your main.py, add:
# schedule.every().monday.at("02:00").do(lambda: asyncio.create_task(updater.weekly_update()))