# 🤖 AgentTools API

> **Essential Tool APIs for Agentic AI Systems**
> Production-ready REST API + MCP Server • Zero-cost data sources • Deploy in minutes

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.1-blueviolet)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🛠️ Available Tools

| Tool | Endpoint | Source | Cost |
|------|----------|--------|------|
| 🌐 **Web Reader** | `POST /tools/web-reader` | Direct HTTP | Free |
| 🔍 **Web Search** | `POST /tools/web-search` | DuckDuckGo | Free |
| ☁️ **Weather** | `POST /tools/weather` | Open-Meteo | Free |
| 🧮 **Calculator** | `POST /tools/calculator` | On-server AST | Free |
| 📰 **News** | `POST /tools/news` | Google News RSS | Free |
| 📝 **Summarizer** | `POST /tools/summarize` | On-server NLP | Free |
| 🌍 **IP Info** | `GET /tools/ip-info` | ip-api.com | Free |

**All external data sources are 100% free — zero API key costs.**

---

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/agent-apis
cd agent-apis
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env to set your DEFAULT_API_KEY
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` to explore the interactive API docs.

### 4. Test

```bash
# Health check (no auth needed)
curl http://localhost:8000/health

# Weather tool
curl -X POST http://localhost:8000/tools/weather \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"location": "London", "forecast_days": 3}'

# Calculator
curl -X POST http://localhost:8000/tools/calculator \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"expression": "sqrt(2) * pi"}'

# Web search
curl -X POST http://localhost:8000/tools/web-search \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"query": "latest AI news", "max_results": 5}'
```

---

## 🔑 Authentication

All tool endpoints require an API key:

```
X-API-Key: your-api-key-here
```

RapidAPI users use `X-RapidAPI-Key` (handled automatically by RapidAPI).

### Tiers

| Tier | Daily Calls |
|------|-------------|
| Free | 100/day |
| Pro | 10,000/day |
| Enterprise | Unlimited |

---

## 📖 API Reference

### POST `/tools/web-reader`
Fetch and extract clean text from any URL.

```json
// Request
{
  "url": "https://example.com/article",
  "max_chars": 5000
}

// Response
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "text": "Clean extracted text...",
  "char_count": 3842
}
```

### POST `/tools/web-search`
Search the web with DuckDuckGo.

```json
// Request
{ "query": "agentic AI trends 2025", "max_results": 5 }

// Response
{
  "query": "agentic AI trends 2025",
  "results": [
    {
      "title": "...",
      "url": "https://...",
      "snippet": "..."
    }
  ]
}
```

### POST `/tools/weather`
Get weather for any location.

```json
// Request
{ "location": "Tokyo", "forecast_days": 3 }

// Response
{
  "location": "Tokyo, Japan",
  "current_temperature_c": 18.5,
  "current_temperature_f": 65.3,
  "wind_speed_kmh": 12.0,
  "weather_description": "Partly cloudy",
  "forecast": [...]
}
```

### POST `/tools/calculator`
Safely evaluate math expressions.

```json
// Request
{ "expression": "sqrt(2) ** 2 + sin(pi/6) * 100" }

// Response
{
  "expression": "sqrt(2) ** 2 + sin(pi/6) * 100",
  "result": 52.0,
  "result_str": "52"
}
```

### POST `/tools/news`
Get latest news by topic.

```json
// Request
{ "topic": "artificial intelligence", "max_articles": 5 }

// Response
{
  "topic": "artificial intelligence",
  "articles": [
    {
      "title": "...",
      "source": "TechCrunch",
      "url": "https://...",
      "published": "2025-11-05 14:00 UTC",
      "summary": "..."
    }
  ]
}
```

### POST `/tools/summarize`
Summarize long text.

```json
// Request
{ "text": "Long article text...", "num_sentences": 3 }

// Response
{
  "original_length": 5000,
  "summary": "Key sentences...",
  "summary_length": 320,
  "compression_ratio": 0.064
}
```

### GET `/tools/ip-info?ip=8.8.8.8`
IP geolocation lookup.

```json
{
  "ip": "8.8.8.8",
  "city": "Mountain View",
  "region": "California",
  "country": "United States",
  "country_code": "US",
  "latitude": 37.386,
  "longitude": -122.0838,
  "timezone": "America/Los_Angeles",
  "isp": "Google LLC"
}
```

---

## 🤖 Using with AI Frameworks

### OpenAI Function Calling
The API auto-generates an OpenAPI spec at `/openapi.json`.
Import it directly into your agent's tool definitions.

### LangChain
```python
from langchain.tools import Tool
import httpx

def search(query: str) -> str:
    r = httpx.post(
        "https://your-api.railway.app/tools/web-search",
        headers={"X-API-Key": "your-key"},
        json={"query": query}
    )
    return str(r.json()["results"])

search_tool = Tool(name="web_search", func=search, description="Search the web")
```

### Claude Tool Use
```python
tools = [{
    "name": "web_search",
    "description": "Search the web and return results",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }
}]
```

### MCP (Claude Desktop / Smithery.ai)
```json
{
  "mcpServers": {
    "agenttools": {
      "command": "python",
      "args": ["/path/to/agent-apis/mcp_server.py"]
    }
  }
}
```

---

## 🚢 Deployment

### Railway (Recommended — Free tier available)

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### Render

Push your code to GitHub and connect the repo at [render.com](https://render.com).
The `render.yaml` config handles everything automatically.

### Docker

```bash
# Build and run
docker-compose up -d

# Or standalone
docker build -t agenttools .
docker run -p 8000:8000 -e DEFAULT_API_KEY=my-key agenttools
```

---

## 💰 Listing on Marketplaces

### RapidAPI
1. Go to [rapidapi.com/provider](https://rapidapi.com/provider)
2. Create new API → "Import from URL"
3. Paste your deployed URL + `/openapi.json`
4. Set pricing plans (suggest: Free 100/mo, Pro $9.99/mo, Enterprise custom)
5. Publish!

### Smithery.ai (MCP Marketplace)
1. Push this repo to GitHub
2. Go to [smithery.ai](https://smithery.ai)
3. Submit your `smithery.yaml` manifest
4. Users can install your tools directly into Claude Desktop

---

## 📊 Admin — Add API Keys

Connect to the SQLite database and add keys manually:

```bash
python -c "
import hashlib, asyncio, aiosqlite

async def add_key(key, name, tier='pro'):
    async with aiosqlite.connect('agent_api.db') as db:
        h = hashlib.sha256(key.encode()).hexdigest()
        await db.execute(
            'INSERT OR IGNORE INTO api_keys (key_hash, name, tier) VALUES (?,?,?)',
            (h, name, tier)
        )
        await db.commit()
        print(f'Added key: {key} ({tier})')

asyncio.run(add_key('my-new-key-123', 'Customer Name', 'pro'))
"
```

---

## 🧪 Run Tests

```bash
# Start server
uvicorn app.main:app --reload &

# Test all endpoints
python -c "
import httpx, json

BASE = 'http://localhost:8000'
KEY = 'test-api-key-12345'
H = {'X-API-Key': KEY}

tests = [
    ('GET', '/health', None),
    ('POST', '/tools/calculator', {'expression': 'sqrt(144)'}),
    ('POST', '/tools/weather', {'location': 'Paris'}),
    ('POST', '/tools/summarize', {'text': 'AI is transforming the world. ' * 20}),
]

for method, path, body in tests:
    r = httpx.request(method, BASE + path, headers=H, json=body)
    print(f'{method} {path}: {r.status_code}')
    print(json.dumps(r.json(), indent=2)[:200])
    print()
"
```

---

## 📁 Project Structure

```
agent-apis/
├── app/
│   ├── main.py          # FastAPI application + all routes
│   ├── auth.py          # API key authentication
│   ├── usage.py         # SQLite usage tracking
│   ├── models.py        # Pydantic request/response schemas
│   └── tools/
│       ├── web_reader.py
│       ├── web_search.py
│       ├── weather.py
│       ├── calculator.py
│       ├── news.py
│       ├── summarizer.py
│       └── ip_info.py
├── mcp_server.py        # MCP server (Smithery.ai compatible)
├── smithery.yaml        # Smithery.ai manifest
├── Dockerfile
├── docker-compose.yml
├── railway.json
├── render.yaml
├── requirements.txt
└── .env.example
```

---

## 📄 License

MIT — free to use, modify, and commercialize.
