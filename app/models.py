from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


# ─── 1. Web to Markdown (Firecrawl style) ────────────────────────────────────

class WebReaderRequest(BaseModel):
    url: str = Field(..., description="The URL to fetch, clean, and convert to Markdown")
    max_length: Optional[int] = Field(15000, description="Maximum characters of Markdown to return", le=50000, ge=100)
    include_links: Optional[bool] = Field(False, description="Whether to extract and list links from the page")


class WebReaderResponse(BaseModel):
    url: str
    title: str
    markdown: str
    content: str
    word_count: int
    estimated_tokens: int
    truncated: bool = False
    links: List[str] = []


# ─── 2. PDF & Document Intelligence ─────────────────────────────────────────

class PDFExtractRequest(BaseModel):
    url: Optional[str] = Field(None, description="Direct URL of the PDF to download and extract")
    file_base64: Optional[str] = Field(None, description="Base64-encoded PDF content")
    max_pages: Optional[int] = Field(15, description="Maximum pages to extract to protect token limits", ge=1, le=100)
    start_page: Optional[int] = Field(1, description="Starting page number (1-indexed)", ge=1)


class PDFPageContent(BaseModel):
    page_number: int
    text: str
    char_count: int


class PDFExtractResponse(BaseModel):
    title: str
    author: str
    total_pages: int
    pages_extracted: int
    word_count: int
    estimated_tokens: int
    pages: List[PDFPageContent]
    full_text: str
    outline: List[str] = []


# ─── 3. Financial & Invoice Intelligence ─────────────────────────────────────

class InvoiceLineItem(BaseModel):
    description: str
    quantity: Optional[float] = 1.0
    unit_price: Optional[float] = None
    total_price: float


class InvoiceData(BaseModel):
    document_type: str = "invoice"
    invoice_number: Optional[str] = None
    purchase_order: Optional[str] = None
    vendor_name: str = "Unknown Vendor"
    vendor_address: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: str = "USD"
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    tax_rate_percent: Optional[float] = None
    total_amount: float = 0.0
    line_items: List[InvoiceLineItem] = []
    payment_terms: Optional[str] = None


class InvoiceExtractRequest(BaseModel):
    url: Optional[str] = Field(None, description="Direct URL of the PDF or image invoice/receipt")
    file_base64: Optional[str] = Field(None, description="Base64-encoded PDF or image file content")
    raw_text: Optional[str] = Field(None, description="Raw OCR or text of the invoice if already extracted")
    currency_hint: Optional[str] = Field("USD", description="Default currency fallback if not detected")


class InvoiceExtractResponse(BaseModel):
    success: bool
    invoice: InvoiceData
    confidence_score: float = Field(..., description="Calculated confidence score between 0.0 and 1.0")
    math_verified: bool = Field(..., description="Whether subtotal + tax equals total_amount")
    processing_time_ms: float
    method_used: str = "deterministic_layout_engine"


# ─── 3. Web Search ───────────────────────────────────────────────────────────

class WebSearchRequest(BaseModel):
    query: str = Field(..., description="The search query string")
    max_results: Optional[int] = Field(5, description="Number of results to return (max 20)", le=20, ge=1)


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchResponse(BaseModel):
    query: str
    results: List[SearchResult]


# ─── 4. Weather ──────────────────────────────────────────────────────────────

class WeatherRequest(BaseModel):
    location: str = Field(..., description="City or location name (e.g. 'London', 'New York', 'Tokyo')")
    forecast_days: Optional[int] = Field(3, description="Number of forecast days (1-7)", ge=1, le=7)


class WeatherDay(BaseModel):
    date: str
    max_temp_c: float
    min_temp_c: float
    precipitation_mm: float
    description: str


class WeatherData(BaseModel):
    location: str
    latitude: float
    longitude: float
    current_temperature_c: float
    current_temperature_f: float
    wind_speed_kmh: float
    weather_description: str
    forecast: List[Dict[str, Any]]


# ─── 5. News Headlines ───────────────────────────────────────────────────────

class NewsRequest(BaseModel):
    topic: str = Field(..., description="News topic or keyword (e.g. 'AI', 'climate change', 'bitcoin')")
    max_articles: Optional[int] = Field(5, description="Number of articles to return (max 20)", le=20, ge=1)


class NewsArticle(BaseModel):
    title: str
    source: str
    url: str
    published: str
    summary: str


class NewsResponse(BaseModel):
    topic: str
    articles: List[NewsArticle]


# ─── 6. Summarizer ───────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    text: str = Field(..., description="Text to summarize (max 50,000 characters)", max_length=50000)
    num_sentences: Optional[int] = Field(3, description="Number of sentences in output summary", ge=1, le=10)


class SummarizeResponse(BaseModel):
    original_length: int
    summary: str
    summary_length: int
    compression_ratio: float


# ─── 7. IP Geolocation ───────────────────────────────────────────────────────

class IPInfoResponse(BaseModel):
    ip: str
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None


# ─── 8. Calculator (Retained for backwards compatibility) ─────────────────────

class CalculatorRequest(BaseModel):
    expression: str = Field(
        ...,
        description="Mathematical expression to evaluate (e.g. '2 + 2 * 10', 'sqrt(144)', 'sin(pi/2)')"
    )


class CalculatorResponse(BaseModel):
    expression: str
    result: float
    result_str: str


# ─── System / Usage Models ───────────────────────────────────────────────────

class UsageResponse(BaseModel):
    api_key: str
    tier: str
    total_calls: int
    daily_calls: int
    daily_limit: int
    remaining_today: int


class ErrorResponse(BaseModel):
    detail: str
