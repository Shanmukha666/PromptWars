"""
Ingestion routes for text and file processing.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from backend.api.dependencies import get_session_id, get_ingestion_service, check_rate_limit
from backend.api.schemas import IngestTextRequest
from backend.services.ingestion_service import IngestionService

router = APIRouter(tags=["Ingestion"])


@router.post("/ingest/text")
async def ingest_text(
    payload: IngestTextRequest,
    request: Request,
    session_id: str = Depends(get_session_id),
    service: IngestionService = Depends(get_ingestion_service),
) -> Dict[str, Any]:
    check_rate_limit(request.client.host if request.client else "unknown", "ingest_text", max_requests=30)
    return await service.ingest_text(payload.text, payload.title, payload.patient_id, session_id=session_id)


@router.post("/ingest/file")
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    patient_id: Optional[str] = Form(None),
    session_id: str = Depends(get_session_id),
    service: IngestionService = Depends(get_ingestion_service),
) -> Dict[str, Any]:
    check_rate_limit(request.client.host if request.client else "unknown", "ingest_file", max_requests=20)
    return await service.ingest_file(file, title, patient_id, session_id=session_id)
