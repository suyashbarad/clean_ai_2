# CleanGreen AI 2.0 🌿
## AI-Powered Smart Waste Management & Urban Cleanliness Intelligence Platform

Developed by **Team Pixel Minds** for the Pune Smart City & Swachh Maharashtra Initiative.

---

## 🌟 Key Features

1. **AI Garbage-Vision Pipeline**:
   - Automated waste classification across 10 categories (Plastic, Organic, Mixed Municipal, Construction Debris, E-Waste, Medical/Bio-hazard, etc.).
   - Confidence scoring, severity classification (Low, Medium, High, Critical), accumulation estimates, and recommended cleanup actions.
   - EXIF GPS extraction from uploaded photos with automatic map pin sync.

2. **DBSCAN Geospatial Hotspot Prediction**:
   - Spatial density clustering (`sklearn.cluster.DBSCAN` with Haversine metric) identifying persistent waste dumping grounds across Pune wards.
   - Predictive risk scoring (0-100) and ward vulnerability index.

3. **MCLP Smart-Bin Placement Optimization**:
   - Mathematical solver for the **Maximum Covering Location Problem** (MCLP).
   - Recommends optimal placement of $K$ new smart dustbins to maximize uncovered demand points with calculated coverage improvement delta.

4. **Sanitation Workforce & TSP Route Optimization**:
   - Traveling Salesperson Problem (TSP) nearest-neighbor algorithm to reorder worker tasks for minimal travel distance and fuel consumption.
   - Mobile-optimized worker dashboard with turn-by-turn navigation and before-and-after resolution photo verification.

5. **Citizen Gamification & Pune Civic Rewards**:
   - Citizen Green Credits wallet (+50 PTS for verified reporting, +25 PTS for completed resolution).
   - Digital voucher redemption for **MahaMetro Pune (₹25 Fare Voucher)**, **PMPML Bus Pass (₹50 Rebate)**, and **PMC Property Tax 5% Rebate**.

6. **CleanBot AI Cleanliness Assistant**:
   - Multilingual conversational assistant powered by **Sarvam AI** (`sarvam-105b-conversations`).
   - Grounded in real-time Pune municipal database metrics and Indian Solid Waste Management Rules 2016.

---

## 🚀 Quickstart Guide

### 1. Run with Python Local Virtual Environment

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (already installed)
pip install -r requirements.txt

# Start FastAPI server
python -m backend.main
```
The application will be live at `http://localhost:8000`.

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

---

## 🏛️ System Architecture

- **Backend**: FastAPI REST architecture, Pydantic validation, SQLite/PostgreSQL schema.
- **AI / ML**: Sarvam AI (`sarvam-105b-conversations`), Scikit-learn DBSCAN clustering, MCLP greedy heuristic optimization, EXIF GPS extractor.
- **Frontend**: Responsive Single-Page Application (HTML5, Tailwind design tokens, Leaflet with OpenStreetMap, Chart.js, FontAwesome 6).
