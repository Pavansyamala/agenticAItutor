# backend/app/core/rag/tavily_client.py
import os
from tavily import TavilyClient

class TavilySearch:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise ValueError("TAVILY_API_KEY not set")
            cls._client = TavilyClient(api_key=api_key)
        return cls._client

    @classmethod
    def search(cls, query: str, max_results: int = 3):
        client = cls.get_client()
        results = client.search(query, max_results=max_results)
        return [r["content"] for r in results["results"]]