"""
Pydantic schemas for request/response validation in FlowSync API.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class ShipmentStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    AT_RISK = "at_risk"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WeatherCondition(int, Enum):
    CLEAR = 0
    RAIN = 1
    STORM = 2
    FOG = 3


class RouteType(int, Enum):
    HIGHWAY = 0
    URBAN = 1
    RURAL = 2


class TrafficLevel(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


# ─── Shipment Schemas ─────────────────────────────────────────────────────────

class ShipmentCreate(BaseModel):
    tracking_id: Optional[str] = None
    origin: str = Field(..., min_length=2, max_length=200)
    destination: str = Field(..., min_length=2, max_length=200)
    carrier: Optional[str] = None
    weight_kg: Optional[float] = Field(None, gt=0)
    distance_km: Optional[float] = Field(None, gt=0)
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    dest_lat: Optional[float] = None
    dest_lng: Optional[float] = None
    route_type: Optional[str] = "highway"
    eta: Optional[datetime] = None
    supplier_id: Optional[int] = None


class ShipmentUpdate(BaseModel):
    status: Optional[ShipmentStatus] = None
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    risk_level: Optional[RiskLevel] = None
    delay_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    eta: Optional[datetime] = None


class ShipmentResponse(BaseModel):
    id: int
    tracking_id: str
    origin: str
    destination: str
    status: ShipmentStatus
    current_lat: Optional[float]
    current_lng: Optional[float]
    origin_lat: Optional[float]
    origin_lng: Optional[float]
    dest_lat: Optional[float]
    dest_lng: Optional[float]
    carrier: Optional[str]
    weight_kg: Optional[float]
    distance_km: Optional[float]
    created_at: datetime
    eta: Optional[datetime]
    risk_level: RiskLevel
    delay_probability: float
    route_type: Optional[str]

    model_config = {"from_attributes": True}


class ShipmentListResponse(BaseModel):
    shipments: List[ShipmentResponse]
    total: int
    active_count: int
    high_risk_count: int
    on_time_percentage: float


# ─── Prediction Schemas ───────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    distance_km: float = Field(..., gt=0, le=20000, description="Distance in kilometers")
    traffic_level: TrafficLevel = Field(..., description="1=Low, 2=Medium, 3=High")
    weather_condition: WeatherCondition = Field(..., description="0=Clear, 1=Rain, 2=Storm, 3=Fog")
    past_delay_avg_hours: float = Field(default=0.0, ge=0.0, le=72.0)
    route_type: RouteType = Field(default=RouteType.HIGHWAY, description="0=Highway, 1=Urban, 2=Rural")
    time_of_day: int = Field(default=12, ge=0, le=23)
    day_of_week: int = Field(default=1, ge=0, le=6)
    shipment_id: Optional[int] = None


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class PredictionResponse(BaseModel):
    delay_probability: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel
    estimated_delay_hours: float
    recommendation: str
    feature_importances: List[FeatureImportance]
    model_version: str = "xgboost-v1"
    predicted_at: datetime


# ─── Route Schemas ────────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    shipment_id: int
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    waypoints: Optional[List[dict]] = None
    optimize: bool = True


class RouteResponse(BaseModel):
    shipment_id: int
    polyline: Optional[str]
    waypoints: List[dict]
    distance_km: float
    duration_min: float
    optimized: bool
    time_saved_hours: Optional[float] = None
    google_maps_url: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Alert Schemas ────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    shipment_id: Optional[int]
    alert_type: str
    message: str
    severity: AlertSeverity
    is_read: bool
    created_at: datetime
    tracking_id: Optional[str] = None

    model_config = {"from_attributes": True}


class AlertMarkRead(BaseModel):
    alert_ids: List[int]


# ─── Dashboard / Analytics Schemas ───────────────────────────────────────────

class KPIResponse(BaseModel):
    total_active_shipments: int
    on_time_percentage: float
    high_risk_count: int
    avg_delay_hours: float
    total_shipments_today: int
    delivered_today: int


class AnalyticsDataPoint(BaseModel):
    label: str
    value: float
    secondary_value: Optional[float] = None


class AnalyticsResponse(BaseModel):
    on_time_trend: List[AnalyticsDataPoint]       # 30-day line chart
    delays_by_route_type: List[AnalyticsDataPoint] # bar chart
    delay_causes: List[AnalyticsDataPoint]          # pie chart
    supplier_reliability: List[AnalyticsDataPoint]  # horizontal bar
    peak_delay_heatmap: List[dict]                  # hour × day matrix


# ─── Model Accuracy Schema ────────────────────────────────────────────────────

class ModelAccuracyResponse(BaseModel):
    accuracy: float
    f1_score: float
    precision: float
    recall: float
    confusion_matrix: List[List[int]]
    feature_importances: List[FeatureImportance]
    training_samples: int
    test_samples: int
    model_version: str


# ─── Supplier Schemas ─────────────────────────────────────────────────────────

class SupplierResponse(BaseModel):
    id: int
    name: str
    location: Optional[str]
    reliability_score: float
    avg_delay_days: float
    total_shipments: int
    on_time_count: int

    model_config = {"from_attributes": True}
