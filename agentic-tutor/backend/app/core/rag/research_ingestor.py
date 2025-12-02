# backend/app/core/rag/research_ingestor.py
import arxiv
from datetime import datetime, timedelta
from .vector_store import VectorStore

def ingest_weekly_papers():
    client = arxiv.Client()
    search = arxiv.Search(
        query="linear algebra OR matrix OR eigenvalue OR vector space",
        max_results=10,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    week_ago = datetime.now() - timedelta(days=7)
    vs = VectorStore()

    for paper in client.results(search):
        if paper.published > week_ago:
            text = f"Title: {paper.title}\nSummary: {paper.summary}\nPublished: {paper.published}"
            vs.add_texts([text], [{"source": "arxiv", "id": paper.entry_id}])
            print(f"Ingested: {paper.title}")