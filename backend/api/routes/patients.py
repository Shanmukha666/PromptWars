"""
Patient profile routes with session isolation.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from backend.api.dependencies import get_session_id, get_patient_repo
from backend.api.schemas import PatientCreateRequest, PatientUpdateRequest
from backend.repositories.patient_repository import PatientRepository

router = APIRouter(tags=["Patients"])


@router.get("/patients")
def list_patients(
    session_id: str = Depends(get_session_id),
    repo: PatientRepository = Depends(get_patient_repo),
) -> Dict[str, Any]:
    return {"items": repo.list_patients(session_id=session_id)}


@router.post("/patients")
def create_patient(
    payload: PatientCreateRequest,
    session_id: str = Depends(get_session_id),
    repo: PatientRepository = Depends(get_patient_repo),
) -> Dict[str, Any]:
    pid = repo.create_patient(
        name=payload.name,
        age=payload.age,
        sex=payload.sex,
        symptoms=payload.symptoms,
        conditions=payload.conditions,
        allergies=payload.allergies,
        medications=payload.medications,
        notes=payload.notes,
        session_id=session_id,
    )
    return {"patient_id": pid}


@router.get("/patients/{patient_id}")
def get_patient(
    patient_id: str,
    session_id: str = Depends(get_session_id),
    repo: PatientRepository = Depends(get_patient_repo),
) -> Dict[str, Any]:
    patient = repo.get_patient(patient_id, session_id=session_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/patients/{patient_id}")
def update_patient(
    patient_id: str,
    payload: PatientUpdateRequest,
    session_id: str = Depends(get_session_id),
    repo: PatientRepository = Depends(get_patient_repo),
) -> Dict[str, Any]:
    success = repo.update_patient(
        patient_id=patient_id,
        name=payload.name,
        age=payload.age,
        sex=payload.sex,
        symptoms=payload.symptoms,
        conditions=payload.conditions,
        allergies=payload.allergies,
        medications=payload.medications,
        notes=payload.notes,
        session_id=session_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found or could not be updated")
    return {"status": "updated", "patient_id": patient_id}


@router.delete("/patients/{patient_id}")
def delete_patient(
    patient_id: str,
    session_id: str = Depends(get_session_id),
    repo: PatientRepository = Depends(get_patient_repo),
) -> Dict[str, Any]:
    deleted = repo.delete_patient(patient_id, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found or access denied")
    return {"status": "deleted", "patient_id": patient_id}
