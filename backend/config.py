import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/cleangreen.db")
SECRET_KEY = os.getenv("SECRET_KEY", "cleangreen-secret-key-2026-pune-smart-city")
UPLOAD_DIR = BASE_DIR / "backend" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_COORDS = {
    "lat": 18.5178,
    "lng": 73.8151,
    "city": "Pune",
    "state": "Maharashtra",
    "locality": "MIT World Peace University, Kothrud"
}
