"""
AgentTools MCP Server
Implements the Model Context Protocol (MCP) over stdio using JSON-RPC 2.0.
Compatible with: Claude Desktop, Cursor, Smithery.ai, and any MCP client.
Works on Python 3.8+.

Run standalone:
    python mcp_server.py

Claude Desktop config (~/.config/Claude/claude_desktop_config.json):
    {
      "mcpServers": {
        "agenttools": {
          "command": "python3",
          "args": ["/path/to/agent-apis/mcp_server.py"]
        }
      }
    }
"""
import sys
import json
import asyncio
import traceback

# ─── Tool definitions ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "invoice_extract",
        "description": "Extract structured financial data (vendor, invoice #, PO #, dates, line items, subtotal, tax, total, currency) from invoices, receipts, and bills, verifying mathematical consistency (subtotal + tax == total). Use when processing accounting documents or receipts. Do not use for generic documents. Read-only and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Public HTTPS URL pointing directly to an invoice image or PDF file (e.g. 'https://example.com/invoice.pdf').",
                },
                "file_base64": {
                    "type": "string",
                    "description": "Base64-encoded file content of the invoice or receipt document.",
                },
                "raw_text": {
                    "type": "string",
                    "description": "Pre-extracted or OCR text content of the invoice to parse directly.",
                },
                "currency_hint": {
                    "type": "string",
                    "description": "3-letter ISO 4217 currency code hint (e.g. 'USD', 'EUR', 'GBP') if no symbol is found.",
                    "default": "USD",
                },
            },
        },
    },
    {
        "name": "pdf_extract",
        "description": "Extract text per page, outlines, document metadata, and accurate token count estimates from PDF documents. Use when ingesting multi-page reports, whitepapers, contracts, or legal documents into context. Read-only and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Direct HTTPS URL to download the target PDF file.",
                },
                "file_base64": {
                    "type": "string",
                    "description": "Base64-encoded binary content of the PDF file.",
                },
                "max_pages": {
                    "type": "integer",
                    "description": "Maximum number of consecutive pages to extract (1 to 50, default 15).",
                    "default": 15,
                },
                "start_page": {
                    "type": "integer",
                    "description": "1-based index of the first page to extract (default 1).",
                    "default": 1,
                },
            },
        },
    },
    {
        "name": "web_reader",
        "description": "Fetch a public webpage URL and extract clean, structured Markdown optimized for LLM token efficiency, stripping headers, footers, ads, and navigation menus. Use when reading articles, blog posts, documentation, or public web pages. Read-only and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The absolute HTTP or HTTPS URL of the webpage to fetch and convert to Markdown.",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum character limit for the returned Markdown content (1,000 to 50,000, default 15000).",
                    "default": 15000,
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to extract and append a catalog of all hyperlinks found in the document.",
                    "default": False,
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the live web using DuckDuckGo to retrieve real-time search results, titles, URLs, and text snippets. Use when you need current facts, external references, or breaking information not in your training data. Read-only and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string, keywords, or question (e.g. 'latest Python PEP releases').",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of search results to return (integer between 1 and 20, default 5).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather conditions (temperature, humidity, wind speed, weather code) and multi-day daily forecasts for any city or geographic location worldwide via Open-Meteo. Use when answering weather queries or trip planning. Read-only and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name (e.g. 'Tokyo', 'London', 'San Francisco') or comma-separated latitude,longitude.",
                },
                "forecast_days": {
                    "type": "integer",
                    "description": "Number of forecast days to return (integer between 1 and 7, default 3).",
                    "default": 3,
                },
            },
            "required": ["location"],
        },
    },
    {
        "name": "calculator",
        "description": "Safely evaluate mathematical and scientific expressions using an isolated AST evaluator without unsafe execution. Supports arithmetic (+, -, *, /, **), trigonometry (sin, cos, tan), logarithms, square roots, and factorials. Use whenever exact numeric precision is required to avoid arithmetic hallucinations. Pure, deterministic, and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression string to evaluate (e.g. 'sqrt(144) + 15 * log(100)').",
                },
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_news",
        "description": "Fetch current news headlines, summaries, sources, and publication timestamps for any topic or keyword via Google News RSS. Use when monitoring breaking news, market updates, or industry trends. Read-only and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic, industry, person, or search keyword to retrieve news stories for (e.g. 'artificial intelligence').",
                },
                "max_articles": {
                    "type": "integer",
                    "description": "Maximum number of news articles to retrieve (integer between 1 and 20, default 5).",
                    "default": 5,
                },
            },
            "required": ["topic"],
        },
    },
    {
        "name": "summarize",
        "description": "Perform extractive text summarization to identify and return the most informative, central sentences from long articles or documents based on term-frequency scoring. Use to compress long context into key points. Pure, deterministic, and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Raw text content to summarize (maximum 50,000 characters).",
                },
                "num_sentences": {
                    "type": "integer",
                    "description": "Number of key summary sentences to extract (integer between 1 and 10, default 3).",
                    "default": 3,
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "get_ip_info",
        "description": "Retrieve geolocation, country, city, geographic coordinates, ISP, and timezone metadata for an IP address. Use to inspect IP locations, detect regional origins, or resolve server IP information. Read-only and idempotent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "IPv4 or IPv6 address to look up (e.g. '8.8.8.8'). Leave empty or blank to look up the caller's public IP address.",
                    "default": "",
                },
            },
        },
    },
]


# ─── Tool execution ───────────────────────────────────────────────────────────

async def execute_tool(name: str, arguments: dict) -> str:
    """Route tool call to the correct handler."""
    from app.models import (
        WebReaderRequest, PDFExtractRequest, InvoiceExtractRequest,
        WebSearchRequest, WeatherRequest, CalculatorRequest, NewsRequest, SummarizeRequest,
    )

    if name == "invoice_extract":
        from app.tools.invoice_extractor import extract_invoice
        result = await extract_invoice(InvoiceExtractRequest(
            url=arguments.get("url"),
            file_base64=arguments.get("file_base64"),
            raw_text=arguments.get("raw_text"),
            currency_hint=arguments.get("currency_hint", "USD"),
        ))
        inv = result.invoice
        lines = [
            f"=== Invoice Data (Confidence: {result.confidence_score*100}%, Math Verified: {result.math_verified}) ===",
            f"Vendor: {inv.vendor_name}",
            f"Invoice #: {inv.invoice_number or 'N/A'}",
            f"Date: {inv.invoice_date or 'N/A'} | Due: {inv.due_date or 'N/A'}",
            f"Customer: {inv.customer_name or 'N/A'}",
            f"Subtotal: {inv.currency} {inv.subtotal or 0.0}",
            f"Tax: {inv.currency} {inv.tax_amount or 0.0}",
            f"Total: {inv.currency} {inv.total_amount}",
            f"Line Items ({len(inv.line_items)}):",
        ]
        for it in inv.line_items:
            lines.append(f" - {it.description}: {it.quantity} x {it.unit_price or 'N/A'} = {inv.currency} {it.total_price}")
        return "\n".join(lines)

    elif name == "pdf_extract":
        from app.tools.pdf_extractor import extract_pdf
        result = await extract_pdf(PDFExtractRequest(
            url=arguments.get("url"),
            file_base64=arguments.get("file_base64"),
            max_pages=arguments.get("max_pages", 15),
            start_page=arguments.get("start_page", 1),
        ))
        lines = [
            f"Title: {result.title or 'N/A'}",
            f"Author: {result.author or 'N/A'}",
            f"Pages: {result.pages_extracted}/{result.total_pages}",
            f"Estimated Tokens: {result.estimated_tokens}",
            "",
            result.full_text,
        ]
        return "\n".join(lines)

    elif name == "web_reader":
        from app.tools.web_reader import read_webpage
        result = await read_webpage(WebReaderRequest(
            url=arguments["url"],
            max_length=arguments.get("max_length", 15000),
            include_links=arguments.get("include_links", False),
        ))
        return f"# {result.title}\nSource: {result.url}\nEstimated Tokens: {result.estimated_tokens}\n\n{result.markdown}"

    elif name == "web_search":
        from app.tools.web_search import search_web
        result = await search_web(WebSearchRequest(
            query=arguments["query"],
            max_results=arguments.get("max_results", 5),
        ))
        lines = [f"Web search results for: '{result.query}'\n"]
        for i, r in enumerate(result.results, 1):
            lines += [f"{i}. {r.title}", f"   URL: {r.url}", f"   {r.snippet}", ""]
        return "\n".join(lines)

    elif name == "get_weather":
        from app.tools.weather import get_weather
        result = await get_weather(WeatherRequest(
            location=arguments["location"],
            forecast_days=arguments.get("forecast_days", 3),
        ))
        lines = [
            f"Weather for {result.location}",
            f"Current: {result.current_temperature_c}°C ({result.current_temperature_f}°F) — {result.weather_description}",
            f"Wind: {result.wind_speed_kmh} km/h", "", "Daily Forecast:",
        ]
        for day in result.forecast:
            lines.append(
                f"  {day['date']}: {day['min_temp_c']}°C – {day['max_temp_c']}°C, "
                f"{day['description']}, Rain: {day['precipitation_mm']}mm"
            )
        return "\n".join(lines)

    elif name == "calculator":
        from app.tools.calculator import calculate
        result = await calculate(CalculatorRequest(expression=arguments["expression"]))
        return f"{result.expression} = {result.result_str}"

    elif name == "get_news":
        from app.tools.news import get_news
        result = await get_news(NewsRequest(
            topic=arguments["topic"],
            max_articles=arguments.get("max_articles", 5),
        ))
        lines = [f"Latest news about '{result.topic}':\n"]
        for i, a in enumerate(result.articles, 1):
            lines += [
                f"{i}. {a.title}",
                f"   Source: {a.source} | {a.published}",
            ]
            if a.summary:
                lines.append(f"   {a.summary}")
            lines += [f"   URL: {a.url}", ""]
        return "\n".join(lines)

    elif name == "summarize":
        from app.tools.summarizer import summarize_text
        result = await summarize_text(SummarizeRequest(
            text=arguments["text"],
            num_sentences=arguments.get("num_sentences", 3),
        ))
        ratio = round(result.compression_ratio * 100, 1)
        return f"Summary ({ratio}% of original, {result.summary_length} chars):\n\n{result.summary}"

    elif name == "get_ip_info":
        from app.tools.ip_info import get_ip_info
        result = await get_ip_info(ip=arguments.get("ip") or None)
        return json.dumps(result.dict(), indent=2)

    else:
        raise ValueError(f"Unknown tool: {name}")


# ─── JSON-RPC / MCP stdio server ─────────────────────────────────────────────

def send_response(response: dict):
    """Write a JSON-RPC response to stdout."""
    line = json.dumps(response) + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()


def send_error(request_id, code: int, message: str):
    send_response({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    })


async def handle_request(request: dict):
    """Handle a single JSON-RPC request."""
    req_id = request.get("id")
    method = request.get("method", "")

    try:
        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "AgentTools",
                        "version": "1.0.0",
                    },
                },
            })

        elif method == "notifications/initialized":
            pass  # Notification — no response needed

        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS},
            })

        elif method == "tools/call":
            params = request.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            result_text = await execute_tool(tool_name, arguments)

            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": False,
                },
            })

        elif method == "ping":
            send_response({"jsonrpc": "2.0", "id": req_id, "result": {}})

        else:
            send_error(req_id, -32601, f"Method not found: {method}")

    except Exception as e:
        error_msg = str(e)
        if req_id is not None:
            send_response({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {error_msg}"}],
                    "isError": True,
                },
            })


async def main():
    """Run the MCP stdio server — reads JSON-RPC from stdin, writes to stdout."""
    loop = asyncio.get_event_loop()

    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            await handle_request(request)

        except json.JSONDecodeError as e:
            send_error(None, -32700, f"Parse error: {e}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
