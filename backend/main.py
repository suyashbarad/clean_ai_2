import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import BASE_DIR, UPLOAD_DIR
from backend.database import init_db, get_connection
from backend.seed_data import seed_all_data

from backend.routes.complaints import router as complaints_router
from backend.routes.workers import router as workers_router
from backend.routes.hotspots import router as hotspots_router
from backend.routes.smart_bins import router as smart_bins_router
from backend.routes.rewards import router as rewards_router
from backend.routes.cleanbot import router as cleanbot_router
from backend.routes.analytics import router as analytics_router

app = FastAPI(
    title="CleanGreen AI 2.0 API",
    description="AI-Powered Smart Waste Management & Urban Cleanliness Intelligence Platform",
    version="2.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()
    # Check if complaints table has rows, if not seed
    conn = get_connection()
    c = conn.cursor()
    count = c.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    conn.close()
    if count == 0:
        seed_all_data()

# Register API Routers
app.include_router(complaints_router)
app.include_router(workers_router)
app.include_router(hotspots_router)
app.include_router(smart_bins_router)
app.include_router(rewards_router)
app.include_router(cleanbot_router)
app.include_router(analytics_router)

# Health check
@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "CleanGreen AI 2.0 Core Platform",
        "location": "Pune, Maharashtra",
        "version": "2.0.0"
    }

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount frontend directory for SPA
FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
