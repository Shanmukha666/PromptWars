"""
Processing and evidence pipeline visualization routes.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends

from backend.api.dependencies import get_session_id, get_provenance_service
from backend.api.schemas import PipelineRequest, MultiAgentRequest
from backend.services.provenance_service import ProvenanceService

router = APIRouter(tags=["Pipeline"])


@router.get("/documents/{document_id}/pipeline")
def get_document_pipeline(
    document_id: str,
    session_id: str = Depends(get_session_id),
    service: ProvenanceService = Depends(get_provenance_service),
) -> Dict[str, Any]:
    return service.get_pipeline(document_id=document_id, session_id=session_id)


@router.post("/pipeline")
def get_pipeline(
    payload: PipelineRequest,
    session_id: str = Depends(get_session_id),
    service: ProvenanceService = Depends(get_provenance_service),
) -> Dict[str, Any]:
    return service.get_pipeline(document_id=payload.document_id, session_id=session_id)


@router.post("/agents/sync")
def agents_sync(
    payload: MultiAgentRequest,
    session_id: str = Depends(get_session_id),
    service: ProvenanceService = Depends(get_provenance_service),
) -> Dict[str, Any]:
    return service.get_pipeline(document_id=payload.document_id, session_id=session_id)
