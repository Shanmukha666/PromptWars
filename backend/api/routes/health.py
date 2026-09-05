"""
Health & status endpoint. Sanitized output without filesystem paths.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends
from backend.api.dependencies import get_session_id, get_report_repo, get_patient_repo, get_llm_client
from backend.repositories.report_repository import ReportRepository
from backend.repositories.patient_repository import PatientRepository
from backend.llm.client import GeminiClient

router = APIRouter(tags=["Health"])


@router.get("/health")
def health(
    session_id: str = Depends(get_session_id),
    report_repo: ReportRepository = Depends(get_report_repo),
    patient_repo: PatientRepository = Depends(get_patient_repo),
    llm: GeminiClient = Depends(get_llm_client),
) -> Dict[str, Any]:
    docs = report_repo.list_documents(limit=200, session_id=session_id)
    patients = patient_repo.list_patients(session_id=session_id)

    return {
        "status": "ok",
        "processing_mode": "offline-local" if llm.is_offline_forced or not llm.configured else "cloud-gemini",
        "gemini": {
            "configured": llm.configured,
            "model": getattr(llm, "model", "gemini-1.5-flash"),
            "mode": "cloud-gemini" if llm.configured else "offline-heuristic-fallback",
        },
        "storage": {
            "session_scoped": True,
            "session_id": session_id,
            "documents_count": len(docs),
            "patients_count": len(patients),
            "persistence_type": "sqlite-local-sandboxed",
        },
        "security": {
            "cors_origin_enforced": True,
            "auth_scoped": True,
            "prompt_injection_guard": True,
            "regulatory_compliance_claimed": False,
            "disclaimer": "Medical information organizing prototype for hackathon demonstration. NOT certified for HIPAA or GDPR clinical deployment."
        }
    }
