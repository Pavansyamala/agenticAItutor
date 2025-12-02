# backend/app/core/rag/vector_store.py
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            cls._instance.db_path = Path("./rag_data/faiss_index")
            cls._instance.db_path.parent.mkdir(exist_ok=True)
            cls._instance._load_or_create()
        return cls._instance

    def _load_or_create(self):
        if self.db_path.exists():
            self.db = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
            logger.info("Loaded existing FAISS index")
        else:
            self.db = FAISS.from_texts(["initial"], self.embeddings)
            self.db.save_local(self.db_path)
            logger.info("Created new FAISS index")

    def add_texts(self, texts: list[str], metadatas: list[dict] = None):
        self.db.add_texts(texts, metadatas)
        self.db.save_local(self.db_path)

    def search(self, query: str, k: int = 5):
        return self.db.similarity_search(query, k=k)