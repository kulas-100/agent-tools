from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict


class WebReaderRequest(BaseModel):
    url: str = Field(..., description="The URL to fetch and extract text from")
    max_chars: Optional[int] = Field(5000, description="Maximum characters to return (max 20000)", le=20000, ge=100)


class WebReaderResponse(BaseModel):
    url: str
    title: str
    text: str
    char_count: int


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


class CalculatorRequest(BaseModel):
    expression: str = Field(
        ...,
        description="Mathematical expression to evaluate (e.g. '2 + 2 * 10', 'sqrt(144)', 'sin(pi/2)')"
    )


class CalculatorResponse(BaseModel):
    expression: str
    result: float
    result_str: str


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


class SummarizeRequest(BaseModel):
    text: str = Field(..., description="Text to summarize (max 50,000 characters)", max_length=50000)
    num_sentences: Optional[int] = Field(3, description="Number of sentences in output summary", ge=1, le=10)


class SummarizeResponse(BaseModel):
    original_length: int
    summary: str
    summary_length: int
    compression_ratio: float


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


class UsageResponse(BaseModel):
    api_key: str
    tier: str
    total_calls: int
    daily_calls: int
    daily_limit: int
    remaining_today: int


class ErrorResponse(BaseModel):
    detail: str
