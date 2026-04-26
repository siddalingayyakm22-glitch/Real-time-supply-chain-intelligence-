"""
SQLAlchemy ORM models for FlowSync.
Defines all database tables with relationships.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from database import Base


class ShipmentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    AT_RISK = "at_risk"


class RiskLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String(50), unique=True, index=True, nullable=False)
    origin = Column(String(200), nullable=False)
    destination = Column(String(200), nullable=False)
    status = Column(SAEnum(ShipmentStatus), default=ShipmentStatus.PENDING, nullable=False)
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    origin_lat = Column(Float, nullable=True)
    origin_lng = Column(Float, nullable=True)
    dest_lat = Column(Float, nullable=True)
    dest_lng = Column(Float, nullable=True)
    carrier = Column(String(100), nullable=True)
    weight_kg = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    eta = Column(DateTime, nullable=True)
    actual_delivery = Column(DateTime, nullable=True)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.LOW)
    delay_probability = Column(Float, default=0.0)
    route_type = Column(String(20), default="highway")  # highway, urban, rural
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Relationships
    routes = relationship("Route", back_populates="shipment", cascade="all, delete-orphan")
    predictions = relationship("DelayPrediction", back_populates="shipment", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="shipment", cascade="all, delete-orphan")
    supplier = relationship("Supplier", back_populates="shipments")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    polyline = Column(Text, nullable=True)          # Encoded Google Maps polyline
    waypoints_json = Column(Text, nullable=True)    # JSON array of lat/lng waypoints
    distance_km = Column(Float, nullable=True)
    duration_min = Column(Float, nullable=True)
    optimized = Column(Boolean, default=False)
    traffic_model = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="routes")


class DelayPrediction(Base):
    __tablename__ = "delay_predictions"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    delay_probability = Column(Float, nullable=False)
    risk_level = Column(SAEnum(RiskLevel), nullable=False)
    estimated_delay_hours = Column(Float, nullable=False)
    # Input features stored for audit/analytics
    distance_km = Column(Float, nullable=True)
    traffic_level = Column(Integer, nullable=True)
    weather_condition = Column(Integer, nullable=True)
    past_delay_avg_hours = Column(Float, nullable=True)
    route_type_encoded = Column(Integer, nullable=True)
    time_of_day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    predicted_at = Column(DateTime, default=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="predictions")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=True)
    alert_type = Column(String(50), nullable=False)  # weather, traffic, delay, eta_deviation
    message = Column(Text, nullable=False)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.WARNING)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    shipment = relationship("Shipment", back_populates="alerts")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(200), nullable=True)
    reliability_score = Column(Float, default=0.8)   # 0.0 – 1.0
    avg_delay_days = Column(Float, default=0.5)
    total_shipments = Column(Integer, default=0)
    on_time_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    shipments = relationship("Shipment", back_populates="supplier")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(200), nullable=False)
    sku = Column(String(100), unique=True, nullable=True)
    quantity = Column(Integer, default=0)
    warehouse_location = Column(String(200), nullable=True)
    reorder_threshold = Column(Integer, default=50)
    unit_cost = Column(Float, nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
