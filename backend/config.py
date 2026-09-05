"""
Centralized Configuration for MedLens Backend.
Handles environment loading, path resolution, and security constants.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Set
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
INDEX_DIR = DATA_DIR / "indexes"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)


class Settings:
    """Application settings with environment variable fallbacks."""

    APP_TITLE: str = "MedLens Clinical Intelligence API"
    APP_VERSION: str = "3.2.0"
    APP_DESCRIPTION: str = (
        "Privacy-hardened clinical data organization prototype. "
        "Not certified for HIPAA/GDPR production use."
    )

    # Storage paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    INDEX_DIR: Path = INDEX_DIR

    # Upload restrictions
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))  # 10MB
    ALLOWED_EXTENSIONS: Set[str] = {".txt", ".pdf", ".json", ".html", ".htm", ".docx", ".xml"}
    MAGIC_SIGNATURES = {
        ".pdf": b"%PDF-",
        ".docx": b"PK\x03\x04",
    }

    # Auth & Scoping
    DEFAULT_SESSION_ID: str = "demo-user-session"

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))

    # LLM Settings
    GEMINI_BASE_URL: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_TIMEOUT: float = float(os.getenv("GEMINI_TIMEOUT", "90"))
    GEMINI_API_KEY: str = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("FEATHERLESS_API_KEY", "").strip()
    )

    @property
    def is_offline_forced(self) -> bool:
        val = os.getenv("MEDLENS_OFFLINE_MODE", "").strip().lower()
        return val in {"1", "true", "yes", "on"}

    @property
    def cors_allowed_origins(self) -> List[str]:
        raw = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
        if raw:
            return [orig.strip() for orig in raw.split(",") if orig.strip()]
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://shanmukha666.github.io",
        ]


settings = Settings()
