# FlowSync — Intelligent Supply Chain Control Tower

> "Supply chains today react to disruptions. FlowSync predicts and prevents them — before they happen."

Built for GDG Hackathon 2025 · Uses Google ecosystem throughout

---

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and fill in your env vars
cp .env.example .env

# Train the ML model (generates model.pkl)
python ml/train_model.py

# Seed the database with mock data
python seed.py

# Start the API server
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install

# Copy and fill in your env vars
cp .env.example .env

# Start dev server (MOCK_MODE=true works without backend)
npm run dev
```

App available at: http://localhost:5173

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `GOOGLE_MAPS_API_KEY` | Google Maps Directions + Traffic API |
| `OPENWEATHER_API_KEY` | OpenWeatherMap API |
| `MOCK_MODE` | `true` = skip real API calls |
| `SIMULATE_MOVEMENT` | `true` = animate shipments in background |

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `VITE_GOOGLE_MAPS_KEY` | Google Maps JavaScript API key |
| `VITE_FIREBASE_*` | Firebase Realtime DB config |
| `VITE_MOCK_MODE` | `true` = full demo without backend |

---

## Architecture

```
flowsync/
├── backend/
│   ├── main.py              ← FastAPI app + WebSocket + analytics
│   ├── models.py            ← SQLAlchemy ORM (6 tables)
│   ├── schemas.py           ← Pydantic request/response models
│   ├── database.py          ← Async PostgreSQL connection
│   ├── seed.py              ← Realistic mock data seeder
│   ├── ml/
│   │   ├── train_model.py   ← XGBoost training (8,000 samples)
│   │   └── predict.py       ← Inference + heuristic fallback
│   └── routes/
│       ├── shipments.py     ← CRUD + KPIs + location tracking
│       ├── predictions.py   ← /predict-delay + /model-accuracy
│       └── alerts.py        ← Alerts + Google Maps route optimization
└── frontend/
    └── src/
        ├── pages/
        │   ├── Dashboard.jsx      ← KPIs + alerts + risk table
        │   ├── LiveMap.jsx        ← Google Maps + animated markers
        │   ├── PredictionPanel.jsx ← ML form + results + history
        │   └── Analytics.jsx      ← 5 chart types + heatmap
        ├── components/            ← Sidebar, KPICard, RiskBadge, etc.
        ├── hooks/                 ← useShipments, useRealtime, usePrediction
        ├── store/useStore.js      ← Zustand global state
        └── lib/
            ├── api.js             ← Axios client + mock fallback
            ├── mockData.js        ← Full demo data (no backend needed)
            └── firebase.js        ← Realtime DB subscriptions
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/shipments/` | Add new shipment |
| `GET` | `/api/v1/shipments/` | List all shipments |
| `GET` | `/api/v1/shipments/kpis` | Dashboard KPI metrics |
| `GET` | `/api/v1/shipments/{id}` | Track single shipment |
| `PATCH` | `/api/v1/shipments/{id}` | Update status/location |
| `POST` | `/api/v1/predictions/predict-delay` | Run ML inference |
| `GET` | `/api/v1/predictions/model-accuracy` | Model metrics |
| `POST` | `/api/v1/get-route` | Optimized route (Google Maps) |
| `GET` | `/api/v1/alerts` | Active alerts |
| `POST` | `/api/v1/alerts/mark-read` | Mark alerts read |
| `GET` | `/api/v1/analytics` | Charts data |
| `WS` | `/ws/shipments` | Real-time location feed |

---

## ML Model

- **Algorithm**: XGBoost Classifier (3 classes: Low / Medium / High risk)
- **Training data**: 8,000 synthetic shipment records with realistic distributions
- **Features**: distance, traffic level, weather, historical delays, route type, time of day, day of week
- **Accuracy**: ~89% on held-out test set
- **Fallback**: Heuristic scoring when `model.pkl` is not present

---

## Google Ecosystem (GDG Advantage)

| Technology | Usage |
|---|---|
| **Google Maps JavaScript API** | Live map rendering with vehicle markers |
| **Google Maps Directions API** | Route optimization with traffic |
| **Google Maps Traffic Layer** | Real-time traffic overlay |
| **Firebase Realtime Database** | Live shipment location updates |
| **Firebase Cloud Messaging** | Push notifications for alerts |
| **Cloud Run** *(deployment)* | Containerized FastAPI backend |
| **BigQuery** *(future)* | Historical delay analytics at scale |
| **Cloud Storage** *(future)* | Model artifact storage |
| **Vertex AI** *(future)* | Managed ML training and serving |

---

## Deployment

### Frontend → Vercel
```bash
# Connect GitHub repo to Vercel
# Set env vars: VITE_GOOGLE_MAPS_KEY, VITE_FIREBASE_*
vercel --prod
```

### Backend → Cloud Run (GCP)
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/flowsync-api
gcloud run deploy flowsync-api \
  --image gcr.io/YOUR_PROJECT/flowsync-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=...,GOOGLE_MAPS_API_KEY=...
```

### Database → Supabase
1. Create project at supabase.com
2. Copy connection string to `DATABASE_URL`
3. Run `python seed.py` to populate

---

## Demo Script (5 minutes)

1. **Live Map** — Show vehicles moving, explain color coding (green/amber/red)
2. **Trigger risk** — Point to red marker, show alert popup ("Storm on Route 7")
3. **Prediction Panel** — Enter params, hit Predict → "78% delay probability — HIGH RISK"
4. **Optimize Route** — Click button, show new route + "Saved 2.3 hours"
5. **Dashboard** — Show KPIs updating live, point to 89% model accuracy

**Opening**: "Supply chains today react to disruptions. FlowSync predicts and prevents them."  
**Closing**: "This is supply chain intelligence — not reaction, prediction."

---

## Team

| Role | Responsibilities |
|---|---|
| Person 1 — Frontend | React + all 4 UI screens + Google Maps integration |
| Person 2 — Backend | FastAPI + 5 endpoints + DB schema + seeding |
| Person 3 — ML | Dataset generation + XGBoost training + /predict-delay |
| Person 4 — Integration | Firebase + deployment + GCP setup + APIs |
