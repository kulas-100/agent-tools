"""
PDF Extractor Tool — Extracts structured text, metadata, and page mapping for AI Agents.
"""
import io
import base64
import httpx
from typing import Optional, List, Dict, Any
from pypdf import PdfReader
from app.models import PDFExtractRequest, PDFExtractResponse, PDFPageContent


async def extract_pdf(request: PDFExtractRequest) -> PDFExtractResponse:
    """
    Extract structured text and metadata from a PDF document (URL or Base64).
    """
    pdf_bytes: bytes = b""

    if request.url:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; AgentToolsBot/2.0; +https://agenttools.dev)"
            )
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=25.0, headers=headers) as client:
            resp = await client.get(str(request.url))
            resp.raise_for_status()
            pdf_bytes = resp.content
    elif request.file_base64:
        try:
            pdf_bytes = base64.b64decode(request.file_base64)
        except Exception as e:
            raise ValueError(f"Invalid base64 payload: {str(e)}")
    else:
        raise ValueError("Either 'url' or 'file_base64' must be provided.")

    stream = io.BytesIO(pdf_bytes)
    reader = PdfReader(stream)
    total_pages = len(reader.pages)

    # Extract metadata
    meta = reader.metadata or {}
    title = meta.title if meta.title else ""
    author = meta.author if meta.author else ""

    # Page range handling
    start_idx = max(0, request.start_page - 1)
    end_idx = min(total_pages, start_idx + request.max_pages)

    extracted_pages: List[PDFPageContent] = []
    full_text_parts: List[str] = []

    for page_num in range(start_idx, end_idx):
        page = reader.pages[page_num]
        page_text = page.extract_text() or ""
        clean_text = page_text.strip()
        
        extracted_pages.append(
            PDFPageContent(
                page_number=page_num + 1,
                text=clean_text,
                char_count=len(clean_text),
            )
        )
        full_text_parts.append(f"--- Page {page_num + 1} ---\n{clean_text}")

    full_text = "\n\n".join(full_text_parts)
    word_count = len(full_text.split())
    # Standard rule of thumb: ~1.3 tokens per word for English text
    estimated_tokens = int(word_count * 1.3)

    # Extract outlines/bookmarks if available
    outlines: List[str] = []
    try:
        outline_items = reader.outline
        if outline_items:
            for item in outline_items:
                if isinstance(item, dict) and "/Title" in item:
                    outlines.append(str(item["/Title"]))
                elif hasattr(item, "title") and item.title:
                    outlines.append(str(item.title))
    except Exception:
        outlines = []

    return PDFExtractResponse(
        title=title,
        author=author,
        total_pages=total_pages,
        pages_extracted=len(extracted_pages),
        word_count=word_count,
        estimated_tokens=estimated_tokens,
        pages=extracted_pages,
        full_text=full_text,
        outline=outlines,
    )
