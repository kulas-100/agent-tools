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
        "name": "web_reader",
        "description": "Fetch and extract clean readable text from any public webpage URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The full URL to fetch"},
                "max_chars": {"type": "integer", "description": "Max characters to return (default 5000)", "default": 5000},
            },
            "required": ["url"],
        },
    },
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo and return structured results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Number of results (1-20)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather",
        "description": "Get current weather and multi-day forecast for any location worldwide.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name (e.g. 'London', 'New York')"},
                "forecast_days": {"type": "integer", "description": "Forecast days (1-7)", "default": 3},
            },
            "required": ["location"],
        },
    },
    {
        "name": "calculator",
        "description": "Safely evaluate math expressions. Supports arithmetic, trig, log, sqrt, factorial.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression (e.g. 'sqrt(144)', 'sin(pi/2)')"},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "get_news",
        "description": "Fetch the latest news headlines and summaries for any topic.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "News topic or keyword"},
                "max_articles": {"type": "integer", "description": "Number of articles (1-20)", "default": 5},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "summarize",
        "description": "Summarize long text into the most important sentences.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to summarize (max 50,000 chars)"},
                "num_sentences": {"type": "integer", "description": "Number of output sentences (1-10)", "default": 3},
            },
            "required": ["text"],
        },
    },
    {
        "name": "get_ip_info",
        "description": "Get geolocation and ISP metadata for an IP address.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "IP address (leave blank for your own IP)", "default": ""},
            },
        },
    },
]


# ─── Tool execution ───────────────────────────────────────────────────────────

async def execute_tool(name: str, arguments: dict) -> str:
    """Route tool call to the correct handler."""
    from app.models import (
        WebReaderRequest, WebSearchRequest, WeatherRequest,
        CalculatorRequest, NewsRequest, SummarizeRequest,
    )

    if name == "web_reader":
        from app.tools.web_reader import read_webpage
        result = await read_webpage(WebReaderRequest(
            url=arguments["url"],
            max_chars=arguments.get("max_chars", 5000),
        ))
        return f"Title: {result.title}\nURL: {result.url}\n\n{result.text}"

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
