"""
Tests for Report Ingestion:
- supported file
- unsupported file
- oversized file (413)
- empty document
- malformed document
"""

import io
import pytest


def test_ingest_supported_text_document(client, auth_headers):
    res = client.post(
        "/api/ingest/text",
        json={
            "title": "Blood Count Report",
            "text": "Hemoglobin: 13.8 g/dL (Ref: 12.0 - 16.0 g/dL)\nWBC: 6.5 x10^3/uL (Ref: 4.0 - 11.0)"
        },
        headers=auth_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert "document_id" in data
    assert data["title"] == "Blood Count Report"
    assert "extracted" in data
    assert "labs" in data["extracted"]
    assert "hemoglobin" in data["extracted"]["labs"]


def test_ingest_unsupported_file_extension(client, auth_headers):
    bad_file = io.BytesIO(b"executable content")
    res = client.post(
        "/api/ingest/file",
        files={"file": ("virus.exe", bad_file, "application/x-msdownload")},
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


def test_ingest_oversized_file(client, auth_headers):
    # 11MB file exceeds 10MB limit
    huge_file = io.BytesIO(b"A" * (11 * 1024 * 1024))
    res = client.post(
        "/api/ingest/file",
        files={"file": ("huge_report.txt", huge_file, "text/plain")},
        headers=auth_headers
    )
    assert res.status_code == 413
    assert "exceeds the maximum" in res.json()["detail"]


def test_ingest_empty_document(client, auth_headers):
    # Empty text
    res_text = client.post(
        "/api/ingest/text",
        json={"text": "   ", "title": "Blank Report"},
        headers=auth_headers
    )
    assert res_text.status_code == 400

    # 0-byte file
    empty_file = io.BytesIO(b"")
    res_file = client.post(
        "/api/ingest/file",
        files={"file": ("blank.txt", empty_file, "text/plain")},
        headers=auth_headers
    )
    assert res_file.status_code == 400


def test_ingest_magic_bytes_mismatch(client, auth_headers):
    fake_pdf = io.BytesIO(b"Plain text labeled as PDF")
    res = client.post(
        "/api/ingest/file",
        files={"file": ("fake.pdf", fake_pdf, "application/pdf")},
        headers=auth_headers
    )
    assert res.status_code == 400
    assert "binary signature" in res.json()["detail"]
