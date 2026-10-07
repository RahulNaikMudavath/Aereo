import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
CERTIFICATES_DIR = STORAGE_DIR / "certificates"
ZIPS_DIR = STORAGE_DIR / "zips"

# Ensure storage directories exist
CERTIFICATES_DIR.mkdir(parents=True, exist_ok=True)
ZIPS_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'certificates.db'}")

# App Settings
APP_TITLE = "Bulk Certificate Generator API"
APP_DESCRIPTION = (
    "Production-ready backend API to accept bulk certificate generation requests, "
    "process them asynchronously with failure isolation, track status, and retrieve certificates."
)
APP_VERSION = "1.0.0"
