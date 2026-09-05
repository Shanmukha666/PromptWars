"""
Tests for Patient Intake:
- valid patient creation
- field validation failures (empty name, out-of-range age)
- updating profile
- retrieving profile
"""

import pytest


def test_create_valid_patient(client, auth_headers):
    payload = {
        "name": "Jane Doe",
        "age": 42,
        "sex": "Female",
        "symptoms": ["fatigue", "dizziness"],
        "conditions": ["anemia"],
        "allergies": ["penicillin"],
        "medications": ["iron supplement"],
        "notes": "Patient reports recurrent tiredness for 3 weeks."
    }
    res = client.post("/api/patients", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "patient_id" in data
    patient_id = data["patient_id"]

    # Verify retrieval
    get_res = client.get(f"/api/patients/{patient_id}", headers=auth_headers)
    assert get_res.status_code == 200
    patient = get_res.json()
    assert patient["name"] == "Jane Doe"
    assert patient["age"] == 42
    assert patient["sex"] == "Female"
    assert "fatigue" in patient["symptoms"]
    assert "penicillin" in patient["allergies"]


def test_patient_validation_failures(client, auth_headers):
    # Empty name failure
    res_empty_name = client.post(
        "/api/patients",
        json={"name": "", "age": 30},
        headers=auth_headers
    )
    assert res_empty_name.status_code == 422

    # Negative age failure
    res_neg_age = client.post(
        "/api/patients",
        json={"name": "Bob", "age": -5},
        headers=auth_headers
    )
    assert res_neg_age.status_code == 422

    # Absurd age failure (>130)
    res_high_age = client.post(
        "/api/patients",
        json={"name": "Bob", "age": 150},
        headers=auth_headers
    )
    assert res_high_age.status_code == 422


def test_update_patient(client, auth_headers):
    res = client.post(
        "/api/patients",
        json={"name": "Initial Name", "age": 25},
        headers=auth_headers
    )
    pid = res.json()["patient_id"]

    update_res = client.put(
        f"/api/patients/{pid}",
        json={"name": "Updated Name", "age": 26, "symptoms": ["headache"]},
        headers=auth_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "updated"

    get_res = client.get(f"/api/patients/{pid}", headers=auth_headers)
    assert get_res.json()["name"] == "Updated Name"
    assert get_res.json()["age"] == 26
    assert get_res.json()["symptoms"] == ["headache"]
