"""
Document management, verification, and deletion routes.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_session_id, get_report_repo
from backend.api.schemas import LabUpdateRequest
from backend.repositories.report_repository import ReportRepository

router = APIRouter(tags=["Documents"])


@router.get("/documents")
def list_documents(
    limit: int = 50,
    patient_id: Optional[str] = None,
    session_id: str = Depends(get_session_id),
    repo: ReportRepository = Depends(get_report_repo),
) -> Dict[str, Any]:
    return {"items": repo.list_documents(limit=limit, patient_id=patient_id, session_id=session_id)}


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    session_id: str = Depends(get_session_id),
    repo: ReportRepository = Depends(get_report_repo),
) -> Dict[str, Any]:
    document = repo.get_document(document_id, session_id=session_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Generate suggested questions
    labs = document.get("extracted", {}).get("labs", {})
    outside = [k for k, v in labs.items() if v.get("status") in {"low", "high"}]
    suggestions = []
    if outside:
        suggestions.append(f"What source reference intervals were used to classify {outside[0]}?")
    suggestions.append("Which observations in this report lack explicit reference ranges?")
    suggestions.append("What medications and allergies are documented?")
    document["suggested_questions"] = suggestions[:4]
    return document


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    session_id: str = Depends(get_session_id),
    repo: ReportRepository = Depends(get_report_repo),
) -> Dict[str, Any]:
    deleted = repo.delete_document(document_id, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found or access denied")
    return {"status": "deleted", "document_id": document_id}


@router.post("/documents/verify-lab")
def verify_or_edit_lab(
    payload: LabUpdateRequest,
    session_id: str = Depends(get_session_id),
    repo: ReportRepository = Depends(get_report_repo),
) -> Dict[str, Any]:
    doc = repo.get_document(payload.document_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    labs = doc.get("extracted", {}).get("labs", {})
    existing = labs.get(payload.test_name, {})
    now_iso = datetime.now(timezone.utc).isoformat()
    action = payload.action or ("edit" if payload.verification_status == "edited" else "verify")

    if action == "remove":
        if payload.test_name in labs:
            del labs[payload.test_name]
        updated_doc = repo.update_document_labs(payload.document_id, labs, session_id=session_id)
        return {"status": "success", "action": "remove", "document": updated_doc, "test_name": payload.test_name}

    audit_trail = list(existing.get("audit_trail", []))
    orig_val = existing.get("original_extracted_value", existing.get("value"))
    if orig_val is None:
        orig_val = payload.original_value if payload.original_value is not None else payload.value

    if action == "mark_incorrect":
        audit_entry = {
            "action": "mark_incorrect",
            "original_value": orig_val,
            "corrected_value": None,
            "changed_at": now_iso,
            "change_source": "user_verified",
            "notes": payload.notes or "Marked incorrect by clinician during review."
        }
        audit_trail.append(audit_entry)
        updated_item = {
            **existing,
            "test_name": payload.test_name,
            "status": "not_assessed",
            "verification_status": "marked_incorrect",
            "provenance_type": "user_verified",
            "verified_notes": payload.notes or "Marked incorrect by clinician.",
            "original_extracted_value": orig_val,
            "audit_trail": audit_trail,
            "updated_at": now_iso
        }
        labs[payload.test_name] = updated_item
        updated_doc = repo.update_document_labs(payload.document_id, labs, session_id=session_id)
        return {"status": "success", "action": "mark_incorrect", "document": updated_doc, "observation": updated_item}

    val = payload.value if payload.value is not None else existing.get("value", 0.0)
    r_min = payload.parsed_min
    r_max = payload.parsed_max
    if r_min is not None and r_max is not None and r_min <= r_max:
        ref_range = {"min": r_min, "max": r_max}
        if val < r_min:
            stat = "low"
        elif val > r_max:
            stat = "high"
        else:
            stat = "normal"
        ref_text = f"Source reference: {payload.reference_range_raw}" if payload.reference_range_raw else f"Source reference: {r_min} - {r_max}"
    else:
        ref_range = None
        stat = "not_assessed"
        ref_text = "Reference range not available in source report."

    if action == "edit":
        v_status = "edited"
        audit_entry = {
            "action": "edit",
            "original_value": orig_val,
            "corrected_value": val,
            "original_unit": existing.get("unit", ""),
            "corrected_unit": payload.unit or existing.get("unit", ""),
            "changed_at": now_iso,
            "change_source": "user_verified",
            "notes": payload.notes or ""
        }
        audit_trail.append(audit_entry)
    elif action == "add":
        v_status = "verified"
        audit_entry = {
            "action": "add",
            "original_value": None,
            "corrected_value": val,
            "changed_at": now_iso,
            "change_source": "user_verified",
            "notes": payload.notes or "Manually added by clinician from source document."
        }
        audit_trail.append(audit_entry)
    else:
        v_status = "verified"
        audit_entry = {
            "action": "verify",
            "original_value": orig_val,
            "corrected_value": val,
            "changed_at": now_iso,
            "change_source": "user_verified",
            "notes": payload.notes or "Verified correct by clinician."
        }
        audit_trail.append(audit_entry)

    updated_item = {
        "test_name": payload.test_name,
        "value": val,
        "unit": payload.unit if payload.unit is not None else existing.get("unit", ""),
        "reference_range": ref_range,
        "source_range_raw": payload.reference_range_raw or existing.get("source_range_raw"),
        "parsed_min": r_min,
        "parsed_max": r_max,
        "reference_range_text": ref_text,
        "status": stat,
        "observation_date": existing.get("observation_date") or (doc.get("created_at", "")[:10] if doc.get("created_at") else None),
        "source_page": payload.source_page or existing.get("source_page", 1),
        "source_snippet": payload.source_snippet or existing.get("source_snippet", ""),
        "extraction_confidence": 1.0,
        "verification_status": v_status,
        "provenance_type": "user_verified",
        "original_extracted_value": orig_val,
        "audit_trail": audit_trail,
        "verified_notes": payload.notes or "",
        "updated_at": now_iso
    }
    labs[payload.test_name] = updated_item
    updated_doc = repo.update_document_labs(payload.document_id, labs, session_id=session_id)
    return {"status": "success", "action": action, "document": updated_doc, "observation": updated_item}
