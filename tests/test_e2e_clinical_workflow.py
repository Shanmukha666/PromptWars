"""
End-to-end Clinical Workflow Happy Path:
  1. Create patient profile
  2. Upload a sample lab report
  3. Extract lab observations
  4. Verify an observation (clinician edit)
  5. Retrieve structured record and confirm observation
  6. Generate safe summary with mandatory footer
"""

import pytest


def test_full_clinical_workflow(client, auth_headers):
    """
    Complete happy-path workflow covering patient intake → report ingestion →
    extraction → verification → structured retrieval → safe summary.
    """
    # ── Step 1: Create Patient ────────────────────────────────────────────
    patient_res = client.post(
        "/api/patients",
        json={
            "name": "E2E Test Patient",
            "age": 58,
            "sex": "Male",
            "symptoms": ["fatigue"],
            "conditions": ["anemia"],
            "allergies": [],
            "medications": ["iron supplement"],
            "notes": "End-to-end test patient."
        },
        headers=auth_headers
    )
    assert patient_res.status_code == 200
    patient_id = patient_res.json()["patient_id"]
    assert patient_id

    # ── Step 2: Upload Sample Lab Report ──────────────────────────────────
    report_text = (
        "LABORATORY REPORT\n"
        "Patient: E2E Test Patient\n"
        "Date: 2024-10-15\n\n"
        "Complete Blood Count:\n"
        "  Hemoglobin: 9.8 g/dL (Ref: 12.0 - 16.0 g/dL)\n"
        "  WBC: 6.2 x10^3/uL (Ref: 4.0 - 11.0 x10^3/uL)\n"
        "  Platelets: 210 x10^3/uL (Ref: 150 - 450 x10^3/uL)\n\n"
        "Chemistry Panel:\n"
        "  Glucose: 105 mg/dL\n"  # No reference range → not_assessed
        "  Creatinine: 1.3 mg/dL (Ref: 0.7 - 1.3 mg/dL)\n\n"
        "Medications: iron supplement\n"
    )
    ingest_res = client.post(
        "/api/ingest/text",
        json={
            "title": "E2E Lab Report",
            "text": report_text,
            "patient_id": patient_id
        },
        headers=auth_headers
    )
    assert ingest_res.status_code == 200
    doc_data = ingest_res.json()
    document_id = doc_data["document_id"]
    assert document_id

    # ── Step 3: Verify Extraction Results ─────────────────────────────────
    labs = doc_data.get("extracted", {}).get("labs", {})
    assert "hemoglobin" in labs, f"Expected hemoglobin in extracted labs, got: {list(labs.keys())}"
    hgb = labs["hemoglobin"]
    assert hgb["value"] == 9.8
    assert hgb["unit"] == "g/dL"
    assert hgb["status"] == "low"  # Below 12.0 ref range

    # WBC should be normal
    if "wbc" in labs:
        assert labs["wbc"]["status"] == "normal"

    # Glucose has no reference range → must be not_assessed
    if "glucose" in labs:
        assert labs["glucose"]["status"] == "not_assessed"

    # ── Step 4: Clinician Verifies/Edits an Observation ───────────────────
    edit_res = client.post(
        "/api/documents/verify-lab",
        json={
            "document_id": document_id,
            "test_name": "hemoglobin",
            "action": "edit",
            "value": 10.0,
            "unit": "g/dL",
            "parsed_min": 12.0,
            "parsed_max": 16.0,
            "reference_range_raw": "12.0 - 16.0 g/dL",
            "notes": "Re-read from source; corrected from 9.8 to 10.0."
        },
        headers=auth_headers
    )
    assert edit_res.status_code == 200
    edited_obs = edit_res.json()["observation"]
    assert edited_obs["value"] == 10.0
    assert edited_obs["verification_status"] == "edited"
    assert edited_obs["provenance_type"] == "user_verified"
    assert edited_obs["original_extracted_value"] == 9.8
    assert edited_obs["status"] == "low"  # 10.0 still below 12.0

    # ── Step 5: Retrieve Structured Record ────────────────────────────────
    doc_res = client.get(f"/api/documents/{document_id}", headers=auth_headers)
    assert doc_res.status_code == 200
    full_doc = doc_res.json()
    assert full_doc["title"] == "E2E Lab Report"

    # The edited value should be persisted
    stored_labs = full_doc.get("extracted", {}).get("labs", {})
    assert stored_labs["hemoglobin"]["value"] == 10.0
    assert stored_labs["hemoglobin"]["verification_status"] == "edited"

    # ── Step 6: Verify Summary Safety ─────────────────────────────────────
    summary = full_doc.get("summary", {})
    if summary:
        # Summary must have mandatory non-diagnostic footer
        from backend.llm.schemas import MANDATORY_FOOTER
        assert summary.get("footer") == MANDATORY_FOOTER

    # ── Step 7: Verify Patient Profile is Retrievable ─────────────────────
    patient_get = client.get(f"/api/patients/{patient_id}", headers=auth_headers)
    assert patient_get.status_code == 200
    assert patient_get.json()["name"] == "E2E Test Patient"

    # ── Step 8: Verify Document Appears in Listing ────────────────────────
    list_res = client.get("/api/documents", headers=auth_headers)
    assert list_res.status_code == 200
    doc_ids = [d["document_id"] for d in list_res.json()["items"]]
    assert document_id in doc_ids
