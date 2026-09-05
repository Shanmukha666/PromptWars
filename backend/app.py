"""
MedLens FastAPI Application Assembly.
Wires middleware, routes, exception handlers, and lifetime events.
"""

import logging
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.exceptions import MedLensError
from backend.api.routes import (
    health,
    patients,
    documents,
    ingestion,
    search,
    pipeline,
)

# Logging with PHI redaction
class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = re.sub(r'(?i)(name|patient|ssn|dob)[:=]\s*[^,\s]+', r'\1=[REDACTED]', record.msg)
        return True

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("medlens")
logger.addFilter(SensitiveDataFilter())


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
    )

    # CORS Middleware with explicit origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Session-ID", "Accept"],
    )

    # Global Exception Handlers
    @app.exception_handler(MedLensError)
    async def medlens_exception_handler(request: Request, exc: MedLensError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled error on %s: %s", request.url.path, type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal processing error occurred. Incident has been logged."}
        )

    # Include Router Modules under /api prefix
    app.include_router(health.router, prefix="/api")
    app.include_router(patients.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(ingestion.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(pipeline.router, prefix="/api")

    return app


app = create_app()
