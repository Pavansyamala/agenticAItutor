# backend/app/core/tools/tavily_search.py
import os
import asyncio
from typing import List, Dict, Any, Optional
import httpx

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", None)
# Default placeholder endpoint; replace with the real Tavily endpoint if different.
TAVILY_API_URL = os.getenv("TAVILY_API_URL", "https://api.tavily.example/search")

# Basic rate-limit / concurrency control for dev
_semaphore = asyncio.Semaphore(4)

async def tavily_search(query: str, top_k: int = 5, timeout: int = 10) -> List[Dict[str, Any]]:
    """
    Perform an async search against Tavily (or a mock fallback).
    Returns a list of dicts: [{"title":..., "snippet":..., "relevance":...}, ...]
    IMPORTANT: This wrapper *never* returns raw URLs to the agent. It returns only concise
    textual snippets that can be embedded into prompts.
    """
    # Mock fallback (if API key not present or endpoint unreachable)
    if not TAVILY_API_KEY or "example" in TAVILY_API_URL:
        # Provide a deterministic small mock for development
        await asyncio.sleep(0.05)
        return [
            {"title": "Mock: PCA in ML", "snippet": "Use SVD to compress data by projecting onto top singular vectors; typical use in image compression.", "relevance": 0.95},
            {"title": "Mock: SVD application", "snippet": "SVD approximates a matrix by low-rank factors; used when data has noise and low-dimensional structure.", "relevance": 0.87}
        ][:top_k]

    headers = {
        "Authorization": f"Bearer {TAVILY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {"q": query, "k": top_k}
    async with _semaphore:
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(TAVILY_API_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # Expected: data["results"] = [{ "title":..., "snippet":..., "score":... }, ...]
                results = []
                for item in data.get("results", [])[:top_k]:
                    results.append({
                        "title": item.get("title", "")[:200],
                        "snippet": item.get("snippet", "")[:1000],
                        "relevance": item.get("score", item.get("relevance", 1.0))
                    })
                return results
            except Exception as e:
                # On any error, return an empty list (agent will still work with RAG/local context)
                return [{"title": "tavily_error", "snippet": f"[Tavily error: {str(e)}] - using no external context", "relevance": 0.0}]
