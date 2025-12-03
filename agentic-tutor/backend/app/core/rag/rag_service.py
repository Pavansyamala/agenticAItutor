# backend/app/core/rag/rag_service.py
from .vector_store import VectorStore
from .tavily_client import TavilySearch
from .arxiv_client import ArxivSearch
from .curriculum_loader import load_curriculum
import logging

logger = logging.getLogger(__name__)

class RAGService:
    _initialized = False

    @classmethod
    def initialize(cls):
        if not cls._initialized:
            texts, metadatas = load_curriculum()
            if texts:
                VectorStore().add_texts(texts, metadatas)
            cls._initialized = True
            logger.info("RAG Service initialized with curriculum")

    @classmethod
    def get_context(cls, query: str, use_tavily: bool = True, use_arxiv: bool = True) -> str:
        cls.initialize()
        vs = VectorStore()

        # 1. FAISS retrieval (normal context)
        docs = vs.search(query, k=5)
        context = "\n\n".join([doc.page_content for doc in docs])

        # 2. Tavily real-time search
        if use_tavily:
            try:
                web_results = TavilySearch.search(
                    f"{query} linear algebra real world application"
                )
                context += "\n\n" + "\n".join(web_results[:2])
            except Exception as e:
                logger.warning(f"Tavily failed: {e}")

        # 3. arXiv research paper search  (NEW)
        if use_arxiv:
            try:
                arxiv_results = ArxivSearch.search(query, limit=2)
                if arxiv_results:
                    context += "\n\n" + "\n\n".join(arxiv_results)
            except Exception as e:
                logger.warning(f"arXiv failed: {e}")

        return context.strip() or "No relevant context found."
