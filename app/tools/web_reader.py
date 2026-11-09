"""
Agentic Markdown Web Scraper — Converts any webpage into clean, LLM-optimized Markdown.
Strips boilerplate, cookie banners, navigation, and ads, preserving structured tables, headers, and code.
"""
import re
import httpx
from typing import List
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from app.models import WebReaderRequest, WebReaderResponse

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AgentToolsBot/2.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REMOVE_TAGS = [
    "script", "style", "nav", "footer", "header",
    "aside", "form", "button", "noscript", "iframe",
    "svg", "figure", "figcaption", "picture", "dialog",
]


async def read_webpage(request: WebReaderRequest) -> WebReaderResponse:
    """Fetch a URL and return clean Markdown optimized for LLM token efficiency."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20,
        headers=HEADERS,
    ) as client:
        response = await client.get(str(request.url))
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    # Remove non-content tags
    for tag in soup(REMOVE_TAGS):
        tag.decompose()

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # Collect links if requested
    extracted_links: List[str] = []
    if request.include_links:
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("http://") or href.startswith("https://"):
                if href not in extracted_links:
                    extracted_links.append(href)
        extracted_links = extracted_links[:50]  # Cap at 50 links

    # Target main content area
    content_area = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|main|article|body", re.I))
        or soup.find(class_=re.compile(r"content|post-content|article-content|entry-content", re.I))
        or soup.body
        or soup
    )

    # Convert HTML to clean Markdown
    markdown_text = md(
        str(content_area),
        heading_style="ATX",
        strip=["script", "style"],
    )

    # Clean redundant blank lines and spaces
    markdown_text = re.sub(r"\n{3,}", "\n\n", markdown_text).strip()

    # Truncate if max_length is specified
    truncated = False
    if request.max_length and len(markdown_text) > request.max_length:
        markdown_text = markdown_text[: request.max_length] + "\n\n...[Content truncated for agent context]"
        truncated = True

    words = len(markdown_text.split())
    estimated_tokens = int(words * 1.3)

    return WebReaderResponse(
        url=str(request.url),
        title=title,
        content=markdown_text,
        markdown=markdown_text,
        word_count=words,
        estimated_tokens=estimated_tokens,
        truncated=truncated,
        links=extracted_links,
    )
