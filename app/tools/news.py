"""
News Tool — Fetches latest news headlines by topic using Google News RSS (free, no API key).
"""
import asyncio
import httpx
import feedparser
from typing import List
from bs4 import BeautifulSoup
from datetime import datetime
from app.models import NewsRequest, NewsResponse, NewsArticle


def _parse_feed(rss_text: str) -> List[dict]:
    """Parse RSS feed text (sync — run in executor)."""
    return feedparser.parse(rss_text)


async def get_news(request: NewsRequest) -> NewsResponse:
    """Fetch and return news articles for a given topic."""
    topic_encoded = request.topic.replace(" ", "+")
    rss_url = (
        f"https://news.google.com/rss/search?"
        f"q={topic_encoded}&hl=en-US&gl=US&ceid=US:en"
    )

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(rss_url)
        resp.raise_for_status()
        rss_text = resp.text

    # feedparser is synchronous — run in thread pool
    loop = asyncio.get_event_loop()
    feed = await loop.run_in_executor(None, lambda: feedparser.parse(rss_text))

    articles: List[NewsArticle] = []

    for entry in feed.entries[: request.max_articles]:
        # Parse publish date
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                dt = datetime(*entry.published_parsed[:6])
                published = dt.strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                published = entry.get("published", "")

        # Strip HTML from summary
        raw_summary = entry.get("summary", "")
        if raw_summary:
            summary = BeautifulSoup(raw_summary, "lxml").get_text().strip()
            # Trim long summaries
            summary = summary[:300] + ("..." if len(summary) > 300 else "")
        else:
            summary = ""

        # Source
        raw_source = entry.get("source", {})
        if isinstance(raw_source, dict):
            source = raw_source.get("title", "Unknown")
        else:
            source = str(raw_source) if raw_source else "Unknown"

        articles.append(
            NewsArticle(
                title=entry.get("title", "No title"),
                source=source,
                url=entry.get("link", ""),
                published=published,
                summary=summary,
            )
        )

    return NewsResponse(topic=request.topic, articles=articles)
