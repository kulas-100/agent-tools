"""
Web Reader Tool — Fetches and extracts clean readable text from any URL.
"""
import httpx
from bs4 import BeautifulSoup
from app.models import WebReaderRequest, WebReaderResponse

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AgentToolsBot/1.0; "
        "+https://agenttools.dev)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

REMOVE_TAGS = [
    "script", "style", "nav", "footer", "header",
    "aside", "form", "button", "noscript", "iframe",
    "svg", "figure", "figcaption", "picture",
]


async def read_webpage(request: WebReaderRequest) -> WebReaderResponse:
    """Fetch a URL and return clean extracted text."""
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=15,
        headers=HEADERS,
    ) as client:
        response = await client.get(request.url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    # Remove boilerplate tags
    for tag in soup(REMOVE_TAGS):
        tag.decompose()

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text(strip=True)

    # Try to get main content area first
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.find("body")
        or soup
    )

    raw_text = main_content.get_text(separator="\n", strip=True)

    # Clean up excessive blank lines
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    text = "\n".join(lines)

    # Truncate to max_chars
    text = text[: request.max_chars]

    return WebReaderResponse(
        url=request.url,
        title=title or "No title",
        text=text,
        char_count=len(text),
    )
