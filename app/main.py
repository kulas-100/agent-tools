"""
AgentTools API — FastAPI application entry point.
Exposes 7 AI agent tools via REST with API key auth and usage tracking.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from app.usage import init_db, record_call, get_usage, TIER_LIMITS
from app.auth import verify_api_key
from app.models import (
    WebReaderRequest, WebReaderResponse,
    WebSearchRequest, WebSearchResponse,
    WeatherRequest, WeatherData,
    CalculatorRequest, CalculatorResponse,
    NewsRequest, NewsResponse,
    SummarizeRequest, SummarizeResponse,
    IPInfoResponse, UsageResponse,
)
from app.tools.web_reader import read_webpage
from app.tools.web_search import search_web
from app.tools.weather import get_weather
from app.tools.calculator import calculate
from app.tools.news import get_news
from app.tools.summarizer import summarize_text
from app.tools.ip_info import get_ip_info


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AgentTools API",
    description="""
## 🤖 AgentTools — Essential Tool APIs for Agentic AI Systems

A production-grade platform providing powerful, ready-to-use tools for AI agents,
compatible with **OpenAI function calling**, **Claude tool use**, **LangChain**, **CrewAI**,
and any framework that can make HTTP requests.

### 🛠️ Available Tools

| Tool | Endpoint | Description |
|------|----------|-------------|
| 🌐 Web Reader | `POST /tools/web-reader` | Fetch & extract clean text from any URL |
| 🔍 Web Search | `POST /tools/web-search` | Search the web via DuckDuckGo |
| ☁️ Weather | `POST /tools/weather` | Real-time weather + forecasts for any location |
| 🧮 Calculator | `POST /tools/calculator` | Safe math expression evaluator |
| 📰 News | `POST /tools/news` | Latest news headlines by topic |
| 📝 Summarizer | `POST /tools/summarize` | Extractive text summarization |
| 🌍 IP Info | `GET /tools/ip-info` | IP geolocation & metadata |

### 🔑 Authentication
Pass your API key in the **`X-API-Key`** header.
RapidAPI users can use the **`X-RapidAPI-Key`** header automatically.

### 📊 Rate Limits
| Tier | Daily Calls | Rate |
|------|-------------|------|
| Free | 100/day | Standard |
| Pro | 10,000/day | Standard |
| Enterprise | Unlimited | Priority |
""",
    version="1.0.0",
    contact={
        "name": "AgentTools API",
        "url": "https://github.com/yourusername/agent-apis",
        "email": "hello@agenttools.dev",
    },
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── System Endpoints ─────────────────────────────────────────────────────────

@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    description="Returns server health status. No authentication required.",
)
async def health_check():
    return {"status": "ok", "version": "1.0.0", "service": "AgentTools API"}


@app.get(
    "/usage",
    response_model=UsageResponse,
    tags=["System"],
    summary="Get my usage stats",
    description="Returns current API key usage stats including daily and total call counts.",
)
async def get_my_usage(auth: dict = Depends(verify_api_key)):
    key_id = auth["key_id"]
    tier = auth["tier"]
    usage = await get_usage(key_id)
    daily_limit = TIER_LIMITS.get(tier, 100)

    return UsageResponse(
        api_key=auth["masked_key"],
        tier=tier,
        total_calls=usage["total_calls"],
        daily_calls=usage["daily_calls"],
        daily_limit=daily_limit,
        remaining_today=max(0, daily_limit - usage["daily_calls"]),
    )


# ─── Tool Endpoints ───────────────────────────────────────────────────────────

@app.post(
    "/tools/web-reader",
    response_model=WebReaderResponse,
    tags=["Tools"],
    summary="Fetch and extract text from a URL",
    description=(
        "Fetches any public URL and returns clean, readable text content. "
        "Removes scripts, ads, navigation, and other boilerplate. "
        "Perfect for agents that need to read and reason about web pages."
    ),
)
async def web_reader_endpoint(
    request: WebReaderRequest,
    auth: dict = Depends(verify_api_key),
):
    try:
        await record_call(auth["key_id"], "/tools/web-reader")
        return await read_webpage(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/tools/web-search",
    response_model=WebSearchResponse,
    tags=["Tools"],
    summary="Search the web",
    description=(
        "Searches the web using DuckDuckGo and returns structured results "
        "(title, URL, snippet). No API key required for the underlying search engine."
    ),
)
async def web_search_endpoint(
    request: WebSearchRequest,
    auth: dict = Depends(verify_api_key),
):
    try:
        await record_call(auth["key_id"], "/tools/web-search")
        return await search_web(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/tools/weather",
    response_model=WeatherData,
    tags=["Tools"],
    summary="Get weather data",
    description=(
        "Returns current weather conditions and a multi-day forecast for any location worldwide. "
        "Powered by Open-Meteo (free, no API key required). "
        "Supports any city name, region, or country."
    ),
)
async def weather_endpoint(
    request: WeatherRequest,
    auth: dict = Depends(verify_api_key),
):
    try:
        await record_call(auth["key_id"], "/tools/weather")
        return await get_weather(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather service error: {e}")


@app.post(
    "/tools/calculator",
    response_model=CalculatorResponse,
    tags=["Tools"],
    summary="Evaluate a math expression",
    description=(
        "Safely evaluates mathematical expressions using AST parsing (no `eval()`). "
        "Supports arithmetic, exponents, modulo, trigonometry (sin, cos, tan), "
        "logarithms (log, log2, log10), sqrt, factorial, and constants (pi, e, tau)."
    ),
)
async def calculator_endpoint(
    request: CalculatorRequest,
    auth: dict = Depends(verify_api_key),
):
    try:
        await record_call(auth["key_id"], "/tools/calculator")
        return await calculate(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/tools/news",
    response_model=NewsResponse,
    tags=["Tools"],
    summary="Get latest news headlines",
    description=(
        "Fetches the latest news articles for any topic using Google News RSS. "
        "Returns structured article data including title, source, URL, publish date, and summary."
    ),
)
async def news_endpoint(
    request: NewsRequest,
    auth: dict = Depends(verify_api_key),
):
    try:
        await record_call(auth["key_id"], "/tools/news")
        return await get_news(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/tools/summarize",
    response_model=SummarizeResponse,
    tags=["Tools"],
    summary="Summarize text",
    description=(
        "Performs extractive text summarization using TF-IDF-inspired sentence scoring. "
        "Selects the most important sentences and returns them in original order. "
        "No external LLM calls — runs entirely on-server at zero cost."
    ),
)
async def summarize_endpoint(
    request: SummarizeRequest,
    auth: dict = Depends(verify_api_key),
):
    try:
        await record_call(auth["key_id"], "/tools/summarize")
        return await summarize_text(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/tools/ip-info",
    response_model=IPInfoResponse,
    tags=["Tools"],
    summary="Get IP geolocation",
    description=(
        "Returns geolocation metadata for an IP address: city, region, country, "
        "coordinates, timezone, and ISP. "
        "Leave the `ip` parameter blank to look up the caller's own IP address."
    ),
)
async def ip_info_endpoint(
    request: Request,
    ip: str = Query(None, description="IP address to look up. Leave blank for your own IP."),
    auth: dict = Depends(verify_api_key),
):
    try:
        await record_call(auth["key_id"], "/tools/ip-info")
        client_host = request.client.host if request.client else None
        return await get_ip_info(ip=ip, client_host=client_host)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"IP lookup error: {e}")
