# 🤖 AgentTools API

> **Production-Grade Tool APIs for Agentic AI Systems & Enterprise Automation**  
> High-Value Financial Document Intelligence • Token-Optimized Web Scraping • MCP Server for Claude & Cursor • Zero Third-Party API Costs

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.1-blueviolet)](https://modelcontextprotocol.io)
[![Glama MCP](https://glama.ai/mcp/servers/kulas-100/agent-tools/badge)](https://glama.ai/mcp/servers/kulas-100/agent-tools)
[![RapidAPI](https://img.shields.io/badge/RapidAPI-Verified-0055FF?logo=rapidapi)](https://rapidapi.com/kulas100/api/agenttools)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🛠️ Flagship Agentic Tools

| Tool | Endpoint | Description | Typical Use Case |
| :--- | :--- | :--- | :--- |
| 🧾 **Invoice & Receipt Intelligence** | `POST /tools/invoice-extract` | Extracts structured JSON (vendor, invoice #, dates, line items, totals, math verify) | Bookkeeping bots, ERP pipelines, CFO agents |
| 📄 **PDF Document Intelligence** | `POST /tools/pdf-extract` | Page-by-page mapping, metadata, outlines, and exact LLM token budget estimation | RAG ingestion, legal & contract analysis |
| 🌐 **Markdown Web Scraper** | `POST /tools/web-reader` | Strips ads, navbars, and cookie banners; returns clean, token-efficient Markdown | Web research agents, documentation readers |
| 🔍 **Web Search** | `POST /tools/web-search` | Live web search via DuckDuckGo with structured snippets | Real-time agent fact-checking |
| 📰 **News Intelligence** | `POST /tools/news` | Topic-based news headlines and summaries via Google News RSS | Market intelligence & news monitoring |
| 📝 **Text Summarizer** | `POST /tools/summarize` | Zero-cost extractive text summarization | Context compression |
| ☁️ **Global Weather** | `POST /tools/weather` | Real-time global weather and multi-day forecasts | Travel & logistics agents |
| 🌍 **IP Geolocation** | `GET /tools/ip-info` | Geolocation, ISP, and network metadata lookup | Security & localization |

---

## ⚡ Feature Highlights

* **Zero External API Costs:** Core tools run on-server with deterministic layout parsing and open data feeds.
* **Math-Verified Invoices:** Automatic check ensures `Subtotal + Tax == Total Amount Due` to prevent accounting hallucination.
* **LLM Token-Budget Aware:** Every document and web extraction returns word counts and estimated token usage.
* **Dual Protocol:** Standard REST API with OpenAPI specification **PLUS** native **Model Context Protocol (MCP)** for Claude Desktop and Cursor.
* **Enterprise Auth & Metering:** Built-in SQLite usage tracking, tier quotas (Free/Pro/Enterprise), and support for both `X-API-Key` and `X-RapidAPI-Key`.

---

## 🚀 Quick Start

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/kulas-100/agent-tools.git
cd agent-tools

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env if you wish to change your master or default API keys
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` in your browser to test endpoints via the interactive Swagger UI.

---

## 📖 API Usage & cURL Examples

All authenticated requests require the `X-API-Key` header (default key: `test-api-key-12345`).

### 1. Extract Invoice / Receipt Data

```bash
curl -X POST http://localhost:8000/tools/invoice-extract \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Acme Cloud Inc.\nTax ID: US-94829104\nINVOICE #INV-2026-8891\nDate: 2026-10-15\nDue: 2026-11-15\nBill To: Wayne Corp\nGPU Compute 2 $ 450.00 $ 900.00\nSubtotal: $ 900.00\nTax: $ 90.00\nTotal: $ 990.00"
  }'
```

**Response:**
```json
{
  "success": true,
  "invoice": {
    "document_type": "invoice",
    "invoice_number": "INV-2026-8891",
    "vendor_name": "Acme Cloud Inc.",
    "vendor_tax_id": "US-94829104",
    "customer_name": "Wayne Corp",
    "invoice_date": "2026-10-15",
    "due_date": "2026-11-15",
    "currency": "USD",
    "subtotal": 900.0,
    "tax_amount": 90.0,
    "total_amount": 990.0,
    "line_items": [
      {
        "description": "GPU Compute",
        "quantity": 2.0,
        "unit_price": 450.0,
        "total_price": 900.0
      }
    ]
  },
  "confidence_score": 1.0,
  "math_verified": true,
  "processing_time_ms": 19.4
}
```

---

### 2. Scrape Webpage to Clean Markdown

```bash
curl -X POST http://localhost:8000/tools/web-reader \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "include_links": true}'
```

---

### 3. Parse PDF Document with Token Budgets

```bash
curl -X POST http://localhost:8000/tools/pdf-extract \
  -H "X-API-Key: test-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf", "max_pages": 5}'
```

---

## 🤖 Model Context Protocol (MCP) Integration

Connect AgentTools directly to **Claude Desktop** or **Cursor**:

### Claude Desktop Configuration (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "agenttools": {
      "command": "/absolute/path/to/agent-tools/.venv/bin/python",
      "args": ["/absolute/path/to/agent-tools/mcp_server.py"]
    }
  }
}
```

---

## 🌐 Public Marketplace Listing

* **RapidAPI Hub:** [rapidapi.com/kulas100/api/agenttools](https://rapidapi.com/kulas100/api/agenttools)
* **Smithery.ai MCP:** Import repository via `smithery.yaml`

---

## 📄 License
MIT License. Free for commercial and personal development.
