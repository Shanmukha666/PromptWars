"""
Tests for Provenance & Audit Trails:
- report-extracted values have source document provenance
- verified edits preserve original values & audit history
- user-provided values are marked user_verified
"""

import pytest


def test_provenance_and_audit_history_on_edit(client, auth_headers):
    # 1. Ingest document
    res = client.post(
        "/api/ingest/text",
        json={
            "title": "Audit Test Report",
            "text": "Hemoglobin: 10.0 g/dL (Ref: 12.0 - 16.0 g/dL)"
        },
        headers=auth_headers
    )
    doc_id = res.json()["document_id"]

    # 2. Clinician edits the observation
    edit_res = client.post(
        "/api/documents/verify-lab",
        json={
            "document_id": doc_id,
            "test_name": "hemoglobin",
            "action": "edit",
            "value": 10.5,
            "unit": "g/dL",
            "notes": "Correction from second reading on page 2."
        },
        headers=auth_headers
    )
    assert edit_res.status_code == 200
    obs = edit_res.json()["observation"]
    assert obs["value"] == 10.5
    assert obs["verification_status"] == "edited"
    assert obs["provenance_type"] == "user_verified"
    assert obs["original_extracted_value"] == 10.0
    assert len(obs["audit_trail"]) == 1
    assert obs["audit_trail"][0]["action"] == "edit"
    assert obs["audit_trail"][0]["original_value"] == 10.0
    assert obs["audit_trail"][0]["corrected_value"] == 10.5


def test_mark_incorrect_observation(client, auth_headers):
    res = client.post(
        "/api/ingest/text",
        json={
            "title": "Error Report",
            "text": "Platelets: 999 x10^3/uL (Ref: 150 - 450)"
        },
        headers=auth_headers
    )
    doc_id = res.json()["document_id"]

    mark_res = client.post(
        "/api/documents/verify-lab",
        json={
            "document_id": doc_id,
            "test_name": "platelets",
            "action": "mark_incorrect",
            "notes": "Typo in lab report."
        },
        headers=auth_headers
    )
    assert mark_res.status_code == 200
    obs = mark_res.json()["observation"]
    assert obs["verification_status"] == "marked_incorrect"
    assert obs["status"] == "not_assessed"


def test_verify_action_preserves_original_value(client, auth_headers):
    """Verify action keeps original value and marks as verified."""
    res = client.post(
        "/api/ingest/text",
        json={
            "title": "Verify Test Report",
            "text": "WBC: 7.5 x10^3/uL (Ref: 4.0 - 11.0)"
        },
        headers=auth_headers
    )
    doc_id = res.json()["document_id"]

    verify_res = client.post(
        "/api/documents/verify-lab",
        json={
            "document_id": doc_id,
            "test_name": "wbc",
            "action": "verify",
            "value": 7.5,
            "unit": "x10^3/uL",
            "notes": "Confirmed by clinician."
        },
        headers=auth_headers
    )
    assert verify_res.status_code == 200
    obs = verify_res.json()["observation"]
    assert obs["verification_status"] == "verified"
    assert obs["provenance_type"] == "user_verified"
    assert len(obs["audit_trail"]) == 1
    assert obs["audit_trail"][0]["action"] == "verify"
