"""
Web Search Tool — Searches the web via DuckDuckGo (no API key required).
"""
import asyncio
from typing import List
from duckduckgo_search import DDGS
from app.models import WebSearchRequest, WebSearchResponse, SearchResult


async def search_web(request: WebSearchRequest) -> WebSearchResponse:
    """Search DuckDuckGo and return structured results."""

    def _sync_search() -> List[dict]:
        with DDGS() as ddgs:
            return list(ddgs.text(request.query, max_results=request.max_results))

    # Run the synchronous DDGS in a thread pool to not block the event loop
    raw_results = await asyncio.get_event_loop().run_in_executor(None, _sync_search)

    results: List[SearchResult] = []
    for r in raw_results:
        results.append(
            SearchResult(
                title=r.get("title", "No title"),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
        )

    return WebSearchResponse(query=request.query, results=results)
