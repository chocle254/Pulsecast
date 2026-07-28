"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel
from typing import Optional


# --- County ---

class CountyBase(BaseModel):
    name: str
    region: str
    livelihood_zone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CountyOut(CountyBase):
    id: int
    current_phase: Optional[str] = None
    current_vci3m: Optional[float] = None
    current_spi: Optional[float] = None


class CountyDetail(CountyOut):
    historical: list[dict] = []
    forecast: Optional[dict] = None
    ai_explanation: Optional[str] = None


# --- Bulletin ---

class BulletinRecord(BaseModel):
    id: int
    county_id: int
    county_name: Optional[str] = None
    month: str
    vci3m: Optional[float] = None
    spi: Optional[float] = None
    phase: str
    source_url: Optional[str] = None
    source_page: Optional[int] = None
    parsed_at: str


# --- Forecast ---

class ForecastPoint(BaseModel):
    week: int
    vci3m: float
    lower: float
    upper: float


class ForecastOut(BaseModel):
    county_id: int
    county_name: Optional[str] = None
    generated_at: str
    forecast_weeks: int
    forecast_values: list[ForecastPoint]
    crossing_date: Optional[str] = None
    crossing_phase: Optional[str] = None
    days_to_crossing: Optional[int] = None
    confidence: Optional[float] = None
    priority_score: Optional[float] = None
    ai_explanation: Optional[str] = None


# --- Priority Queue ---

class PriorityQueueItem(BaseModel):
    rank: int
    county_id: int
    county_name: str
    region: str
    livelihood_zone: str
    current_phase: str
    current_vci3m: Optional[float] = None
    forecast_vci3m: Optional[float] = None
    crossing_date: Optional[str] = None
    crossing_phase: Optional[str] = None
    days_to_crossing: Optional[int] = None
    confidence: Optional[float] = None
    priority_score: float
    sparkline_data: list[float] = []
    ai_summary: Optional[str] = None


# --- Backtest ---

class BacktestRecord(BaseModel):
    county_id: int
    county_name: Optional[str] = None
    month: str
    predicted_phase: str
    actual_phase: str
    predicted_vci3m: Optional[float] = None
    actual_vci3m: Optional[float] = None
    hit: bool


class BacktestSummary(BaseModel):
    total_predictions: int
    correct_predictions: int
    hit_rate: float
    false_alarm_rate: float
    counties: list[dict] = []


# --- Map ---

class MapCountyData(BaseModel):
    county_id: int
    county_name: str
    current_phase: str
    forecast_phase: Optional[str] = None
    days_to_crossing: Optional[int] = None
    priority_score: Optional[float] = None
    vci3m: Optional[float] = None


# --- LLM ---

class ExplanationRequest(BaseModel):
    county_id: int
    include_sensitivity: bool = False


class ExplanationResponse(BaseModel):
    county_id: int
    county_name: str
    explanation: str
    citations: list[dict] = []
    generated_at: str
