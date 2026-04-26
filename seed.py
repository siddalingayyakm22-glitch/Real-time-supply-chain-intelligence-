"""
FlowSync Database Seeder
Populates the database with realistic mock data for demo purposes.

Run: python seed.py
"""

import asyncio
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, init_db
from models import (
    Shipment, Route, DelayPrediction, Alert, Supplier, Inventory,
    ShipmentStatus, RiskLevel, AlertSeverity
)

# ─── Seed Data ────────────────────────────────────────────────────────────────

SUPPLIERS = [
    {"name": "FastFreight Co.", "location": "Chicago, IL", "reliability_score": 0.942, "avg_delay_days": 0.2},
    {"name": "GlobalShip Ltd.", "location": "Los Angeles, CA", "reliability_score": 0.887, "avg_delay_days": 0.5},
    {"name": "QuickMove Inc.", "location": "Houston, TX", "reliability_score": 0.821, "avg_delay_days": 0.8},
    {"name": "PrimeLogistics", "location": "New York, NY", "reliability_score": 0.795, "avg_delay_days": 1.1},
    {"name": "EcoTransport", "location": "Seattle, WA", "reliability_score": 0.913, "avg_delay_days": 0.3},
]

# Major US city coordinates for realistic routes
CITIES = [
    ("New York, NY",       40.7128,  -74.0060),
    ("Los Angeles, CA",    34.0522, -118.2437),
    ("Chicago, IL",        41.8781,  -87.6298),
    ("Houston, TX",        29.7604,  -95.3698),
    ("Phoenix, AZ",        33.4484, -112.0740),
    ("Philadelphia, PA",   39.9526,  -75.1652),
    ("San Antonio, TX",    29.4241,  -98.4936),
    ("San Diego, CA",      32.7157, -117.1611),
    ("Dallas, TX",         32.7767,  -96.7970),
    ("San Jose, CA",       37.3382, -121.8863),
    ("Austin, TX",         30.2672,  -97.7431),
    ("Jacksonville, FL",   30.3322,  -81.6557),
    ("Seattle, WA",        47.6062, -122.3321),
    ("Denver, CO",         39.7392, -104.9903),
    ("Nashville, TN",      36.1627,  -86.7816),
    ("Atlanta, GA",        33.7490,  -84.3880),
    ("Miami, FL",          25.7617,  -80.1918),
    ("Minneapolis, MN",    44.9778,  -93.2650),
    ("Portland, OR",       45.5051, -122.6750),
    ("Las Vegas, NV",      36.1699, -115.1398),
]

CARRIERS = ["FedEx", "UPS", "DHL", "USPS", "Amazon Logistics", "XPO Logistics", "J.B. Hunt"]
ROUTE_TYPES = ["highway", "urban", "rural"]
PRODUCTS = [
    "Electronics", "Pharmaceuticals", "Automotive Parts", "Food & Beverage",
    "Clothing", "Industrial Equipment", "Consumer Goods", "Medical Devices",
]

ALERT_TEMPLATES = [
    ("weather", "Storm warning on Route {route} — High delay risk", AlertSeverity.CRITICAL),
    ("traffic", "Heavy traffic detected near {city} — ETA extended by {mins} minutes", AlertSeverity.WARNING),
    ("delay", "Shipment {tid} is running {hours}h behind schedule", AlertSeverity.WARNING),
    ("eta_deviation", "ETA deviation > 2 hours detected for shipment {tid}", AlertSeverity.CRITICAL),
    ("carrier", "Carrier {carrier} reporting operational delays in {region}", AlertSeverity.INFO),
]


def random_city_pair():
    origin, dest = random.sample(CITIES, 2)
    return origin, dest


def haversine(lat1, lng1, lat2, lng2) -> float:
    """Approximate distance in km between two coordinates."""
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def seed(db: AsyncSession):
    print("🌱 Seeding FlowSync database...")

    # ── Suppliers ─────────────────────────────────────────────────────────────
    supplier_records = []
    for s in SUPPLIERS:
        total = random.randint(200, 800)
        on_time = int(total * s["reliability_score"])
        supplier = Supplier(
            name=s["name"],
            location=s["location"],
            reliability_score=s["reliability_score"],
            avg_delay_days=s["avg_delay_days"],
            total_shipments=total,
            on_time_count=on_time,
        )
        db.add(supplier)
        supplier_records.append(supplier)

    await db.flush()
    print(f"  ✅ {len(supplier_records)} suppliers created")

    # ── Inventory ─────────────────────────────────────────────────────────────
    warehouses = ["Chicago Hub", "LA Distribution", "NYC Fulfillment", "Dallas Center", "Seattle Depot"]
    for i, product in enumerate(PRODUCTS):
        qty = random.randint(10, 500)
        threshold = random.randint(30, 100)
        inv = Inventory(
            product_name=product,
            sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
            quantity=qty,
            warehouse_location=random.choice(warehouses),
            reorder_threshold=threshold,
            unit_cost=round(random.uniform(5, 500), 2),
            supplier_id=random.choice(supplier_records).id,
        )
        db.add(inv)

    await db.flush()
    print(f"  ✅ {len(PRODUCTS)} inventory items created")

    # ── Shipments ─────────────────────────────────────────────────────────────
    shipment_records = []
    statuses = [
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.IN_TRANSIT,
        ShipmentStatus.AT_RISK,
        ShipmentStatus.DELIVERED,
        ShipmentStatus.DELAYED,
        ShipmentStatus.PENDING,
    ]

    for i in range(40):
        origin_city, dest_city = random_city_pair()
        origin_name, origin_lat, origin_lng = origin_city
        dest_name, dest_lat, dest_lng = dest_city

        distance = haversine(origin_lat, origin_lng, dest_lat, dest_lng)
        status = random.choice(statuses)
        risk = random.choices(
            [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH],
            weights=[0.5, 0.3, 0.2]
        )[0]

        # Progress along route (0.0 = at origin, 1.0 = at destination)
        progress = random.uniform(0.1, 0.9) if status == ShipmentStatus.IN_TRANSIT else 0.0
        if status == ShipmentStatus.DELIVERED:
            progress = 1.0

        current_lat = origin_lat + progress * (dest_lat - origin_lat)
        current_lng = origin_lng + progress * (dest_lng - origin_lng)

        created_at = datetime.utcnow() - timedelta(hours=random.randint(1, 72))
        eta = created_at + timedelta(hours=distance / 60 + random.uniform(-2, 6))

        delay_prob = {"Low": random.uniform(0, 0.35), "Medium": random.uniform(0.35, 0.65), "High": random.uniform(0.65, 0.95)}[risk.value]

        shipment = Shipment(
            tracking_id=f"FS-{uuid.uuid4().hex[:8].upper()}",
            origin=origin_name,
            destination=dest_name,
            status=status,
            current_lat=round(current_lat, 6),
            current_lng=round(current_lng, 6),
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            dest_lat=dest_lat,
            dest_lng=dest_lng,
            carrier=random.choice(CARRIERS),
            weight_kg=round(random.uniform(10, 5000), 1),
            distance_km=round(distance, 1),
            created_at=created_at,
            eta=eta,
            risk_level=risk,
            delay_probability=round(delay_prob, 4),
            route_type=random.choice(ROUTE_TYPES),
            supplier_id=random.choice(supplier_records).id,
            actual_delivery=eta if status == ShipmentStatus.DELIVERED else None,
        )
        db.add(shipment)
        shipment_records.append(shipment)

    await db.flush()
    print(f"  ✅ {len(shipment_records)} shipments created")

    # ── Delay Predictions ─────────────────────────────────────────────────────
    for shipment in random.sample(shipment_records, min(20, len(shipment_records))):
        pred = DelayPrediction(
            shipment_id=shipment.id,
            delay_probability=shipment.delay_probability,
            risk_level=shipment.risk_level,
            estimated_delay_hours=round(shipment.delay_probability * 8, 2),
            distance_km=shipment.distance_km,
            traffic_level=random.randint(1, 3),
            weather_condition=random.randint(0, 3),
            past_delay_avg_hours=round(random.uniform(0, 5), 2),
            route_type_encoded=ROUTE_TYPES.index(shipment.route_type),
            time_of_day=random.randint(0, 23),
            day_of_week=random.randint(0, 6),
            predicted_at=shipment.created_at + timedelta(minutes=random.randint(5, 60)),
        )
        db.add(pred)

    await db.flush()
    print("  ✅ Delay predictions created")

    # ── Alerts ────────────────────────────────────────────────────────────────
    alert_count = 0
    high_risk_shipments = [s for s in shipment_records if s.risk_level == RiskLevel.HIGH]

    for shipment in high_risk_shipments[:8]:
        template = random.choice(ALERT_TEMPLATES)
        alert_type, msg_template, severity = template
        message = msg_template.format(
            route=f"Route-{random.randint(1, 10)}",
            city=shipment.destination.split(",")[0],
            mins=random.randint(15, 90),
            hours=round(random.uniform(1, 5), 1),
            tid=shipment.tracking_id,
            carrier=shipment.carrier,
            region=shipment.origin.split(",")[1].strip() if "," in shipment.origin else "Region",
        )
        alert = Alert(
            shipment_id=shipment.id,
            alert_type=alert_type,
            message=message,
            severity=severity,
            is_read=random.choice([True, False]),
            created_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
        )
        db.add(alert)
        alert_count += 1

    # Add a few general alerts
    for _ in range(4):
        alert = Alert(
            shipment_id=None,
            alert_type="system",
            message=random.choice([
                "Weather advisory: Heavy rain expected in Midwest corridor",
                "Port congestion reported at Los Angeles — expect 4-6h delays",
                "Fuel surcharge increase effective next week — review carrier contracts",
                "System maintenance scheduled for Sunday 2:00 AM UTC",
            ]),
            severity=random.choice([AlertSeverity.INFO, AlertSeverity.WARNING]),
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 12)),
        )
        db.add(alert)
        alert_count += 1

    await db.flush()
    print(f"  ✅ {alert_count} alerts created")

    await db.commit()
    print("\n🎉 Database seeded successfully!")
    print(f"   Suppliers: {len(supplier_records)}")
    print(f"   Shipments: {len(shipment_records)}")
    print(f"   Alerts: {alert_count}")


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        await seed(db)


if __name__ == "__main__":
    asyncio.run(main())
