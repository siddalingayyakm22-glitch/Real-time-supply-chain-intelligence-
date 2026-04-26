"""
FlowSync — Intelligent Supply Chain Control Tower
FastAPI application entry point.

Run: uvicorn main:app --reload --port 8000
"""

import os
import asyncio
import json
import random
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from sqlalchemy import select, update

load_dotenv()

from database import init_db, AsyncSessionLocal
from models import Shipment, Alert, ShipmentStatus, RiskLevel, AlertSeverity
from routes.shipments import router as shipments_router
from routes.predictions import router as predictions_router
from routes.alerts import router as alerts_router
from ml.predict import predictor

MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"
SIMULATE_MOVEMENT = os.getenv("SIMULATE_MOVEMENT", "true").lower() == "true"


# ─── WebSocket Connection Manager ─────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send JSON message to all connected clients."""
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ─── Background Simulation Task ───────────────────────────────────────────────

async def simulate_shipment_movement():
    """
    Background task: moves in-transit shipments along their route
    and broadcasts location updates every 3 seconds.
    Also triggers risk alerts when conditions are met.
    """
    while True:
        await asyncio.sleep(3)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Shipment).where(
                        Shipment.status.in_([ShipmentStatus.IN_TRANSIT, ShipmentStatus.AT_RISK])
                    )
                )
                shipments = result.scalars().all()

                updates = []
                for shipment in shipments:
                    if not all([
                        shipment.current_lat, shipment.current_lng,
                        shipment.dest_lat, shipment.dest_lng
                    ]):
                        continue

                    # Move 0.5–1.5% of remaining distance toward destination
                    progress = random.uniform(0.005, 0.015)
                    new_lat = shipment.current_lat + progress * (shipment.dest_lat - shipment.current_lat)
                    new_lng = shipment.current_lng + progress * (shipment.dest_lng - shipment.current_lng)

                    # Add slight jitter for realism
                    new_lat += random.uniform(-0.0005, 0.0005)
                    new_lng += random.uniform(-0.0005, 0.0005)

                    shipment.current_lat = round(new_lat, 6)
                    shipment.current_lng = round(new_lng, 6)

                    # Check if arrived (within ~1km of destination)
                    dist_to_dest = abs(new_lat - shipment.dest_lat) + abs(new_lng - shipment.dest_lng)
                    if dist_to_dest < 0.01:
                        shipment.status = ShipmentStatus.DELIVERED
                        shipment.actual_delivery = datetime.utcnow()

                    updates.append({
                        "type": "location_update",
                        "tracking_id": shipment.tracking_id,
                        "lat": shipment.current_lat,
                        "lng": shipment.current_lng,
                        "status": shipment.status.value,
                        "risk_level": shipment.risk_level.value,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

                await db.commit()

                # Broadcast all updates
                for update_msg in updates:
                    await manager.broadcast(update_msg)

        except Exception as e:
            print(f"[SIM] Error in movement simulation: {e}")


# ─── App Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    print("🚀 FlowSync starting up...")

    # Initialize database tables
    await init_db()
    print("✅ Database initialized")

    # Load ML model
    predictor.load()

    # Start background simulation
    if SIMULATE_MOVEMENT:
        task = asyncio.create_task(simulate_shipment_movement())
        print("✅ Shipment movement simulation started")

    yield

    # Cleanup
    if SIMULATE_MOVEMENT:
        task.cancel()
    print("👋 FlowSync shutting down")


# ─── App Instance ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="FlowSync API",
    description="Intelligent Supply Chain Control Tower — GDG Hackathon",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow React dev server and production domains
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://flowsync.vercel.app"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(shipments_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")


# ─── Health & Root ────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "FlowSync API",
        "version": "1.0.0",
        "status": "operational",
        "mock_mode": MOCK_MODE,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "ml_model_loaded": predictor.is_loaded,
    }


# ─── Analytics Endpoint ───────────────────────────────────────────────────────

@app.get("/api/v1/analytics", tags=["Analytics"])
async def get_analytics():
    """
    Return pre-computed analytics data for charts.
    In production this would query the DB; here we return
    realistic mock data that looks great in the demo.
    """
    from datetime import date, timedelta

    # 30-day on-time trend
    on_time_trend = []
    base_pct = 87.0
    for i in range(30):
        day = date.today() - timedelta(days=29 - i)
        pct = base_pct + random.uniform(-5, 5)
        on_time_trend.append({"label": day.strftime("%b %d"), "value": round(pct, 1)})

    # Delays by route type
    delays_by_route = [
        {"label": "Highway", "value": 12.3},
        {"label": "Urban", "value": 28.7},
        {"label": "Rural", "value": 19.4},
    ]

    # Delay causes (pie)
    delay_causes = [
        {"label": "Traffic", "value": 38},
        {"label": "Weather", "value": 27},
        {"label": "Carrier", "value": 21},
        {"label": "Customs", "value": 9},
        {"label": "Other", "value": 5},
    ]

    # Supplier reliability
    supplier_reliability = [
        {"label": "FastFreight Co.", "value": 94.2},
        {"label": "GlobalShip Ltd.", "value": 88.7},
        {"label": "QuickMove Inc.", "value": 82.1},
        {"label": "PrimeLogistics", "value": 79.5},
        {"label": "EcoTransport", "value": 91.3},
    ]

    # Peak delay heatmap (hour 0-23 × day 0-6)
    heatmap = []
    for day in range(7):
        for hour in range(24):
            # Rush hours and weekdays have higher delay rates
            base = 5
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                base += 20
            if day < 5:  # weekday
                base += 10
            value = base + random.randint(0, 15)
            heatmap.append({"day": day, "hour": hour, "value": value})

    return {
        "on_time_trend": on_time_trend,
        "delays_by_route_type": delays_by_route,
        "delay_causes": delay_causes,
        "supplier_reliability": supplier_reliability,
        "peak_delay_heatmap": heatmap,
    }


# ─── WebSocket Endpoint ───────────────────────────────────────────────────────

@app.websocket("/ws/shipments")
async def websocket_shipments(websocket: WebSocket):
    """
    WebSocket endpoint for real-time shipment location updates.
    Client receives: { type, tracking_id, lat, lng, status, risk_level, timestamp }
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; server pushes updates via broadcast()
            data = await websocket.receive_text()
            # Client can send { "subscribe": "FS-XXXX" } to filter updates
    except WebSocketDisconnect:
        manager.disconnect(websocket)
