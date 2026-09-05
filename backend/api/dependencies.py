"""
FastAPI dependencies: Session resolution, Rate limiting, and Service injection.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import Header, HTTPException, Request, status

from backend.config import settings
from backend.repositories.patient_repository import PatientRepository
from backend.repositories.report_repository import ReportRepository
from backend.services.extraction_service import ExtractionService
from backend.services.summary_service import SummaryService
from backend.services.provenance_service import ProvenanceService
from backend.services.comparison_service import ComparisonService
from backend.services.ingestion_service import IngestionService
from backend.llm.client import GeminiClient

RATE_LIMIT_BUCKET: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(client_ip: str, endpoint: str = "general", max_requests: int = 60, window_secs: float = 60.0):
    key = f"{client_ip}:{endpoint}"
    now = time.time()
    RATE_LIMIT_BUCKET[key] = [ts for ts in RATE_LIMIT_BUCKET[key] if now - ts < window_secs]
    if len(RATE_LIMIT_BUCKET[key]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({max_requests} req/{int(window_secs)}s). Please wait before retrying."
        )
    RATE_LIMIT_BUCKET[key].append(now)


def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    if x_session_id and x_session_id.strip():
        return x_session_id.strip()
    return settings.DEFAULT_SESSION_ID


# Singleton Service Instances
patient_repo = PatientRepository()
report_repo = ReportRepository()
llm_client = GeminiClient()
extraction_service = ExtractionService()
summary_service = SummaryService(llm_client)
provenance_service = ProvenanceService(report_repo)
comparison_service = ComparisonService()
ingestion_service = IngestionService(report_repo, extraction_service, summary_service, llm_client, patient_repo)


def get_patient_repo() -> PatientRepository:
    return patient_repo


def get_report_repo() -> ReportRepository:
    return report_repo


def get_llm_client() -> GeminiClient:
    return llm_client


def get_extraction_service() -> ExtractionService:
    return extraction_service


def get_summary_service() -> SummaryService:
    return summary_service


def get_provenance_service() -> ProvenanceService:
    return provenance_service


def get_comparison_service() -> ComparisonService:
    return comparison_service


def get_ingestion_service() -> IngestionService:
    return ingestion_service
