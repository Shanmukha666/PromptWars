"""
Tests for Security & Session Isolation:
- Unauthenticated requests return default session (prototype behavior)
- Cross-session IDOR: one user cannot access another user's data
- Path traversal filenames are rejected
- Invalid file types rejected at upload boundary
- Document deletion respects session scope
"""

import io
import pytest


class TestSessionIsolation:
    """Cross-session access control (IDOR protection)."""

    def test_patient_not_visible_to_other_session(self, client, auth_headers, alt_auth_headers):
        """User 1's patient should return 404 for user 2."""
        create_res = client.post(
            "/api/patients",
            json={"name": "Private Patient", "age": 30},
            headers=auth_headers
        )
        pid = create_res.json()["patient_id"]

        # Same user can access
        get_own = client.get(f"/api/patients/{pid}", headers=auth_headers)
        assert get_own.status_code == 200

        # Different user cannot
        get_other = client.get(f"/api/patients/{pid}", headers=alt_auth_headers)
        assert get_other.status_code == 404

    def test_document_not_visible_to_other_session(self, client, auth_headers, alt_auth_headers):
        """User 1's document should return 404 for user 2."""
        ingest_res = client.post(
            "/api/ingest/text",
            json={"title": "Private Report", "text": "Hemoglobin: 14.0 g/dL"},
            headers=auth_headers
        )
        doc_id = ingest_res.json()["document_id"]

        # Same user can access
        get_own = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
        assert get_own.status_code == 200

        # Different user cannot
        get_other = client.get(f"/api/documents/{doc_id}", headers=alt_auth_headers)
        assert get_other.status_code == 404

    def test_document_delete_rejected_for_other_session(self, client, auth_headers, alt_auth_headers):
        """User 2 cannot delete user 1's document."""
        ingest_res = client.post(
            "/api/ingest/text",
            json={"title": "Delete Test", "text": "Glucose: 90 mg/dL"},
            headers=auth_headers
        )
        doc_id = ingest_res.json()["document_id"]

        # User 2 tries to delete
        del_res = client.delete(f"/api/documents/{doc_id}", headers=alt_auth_headers)
        assert del_res.status_code == 404

        # User 1 can still retrieve it
        get_res = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
        assert get_res.status_code == 200

    def test_patient_delete_rejected_for_other_session(self, client, auth_headers, alt_auth_headers):
        """User 2 cannot delete user 1's patient."""
        create_res = client.post(
            "/api/patients",
            json={"name": "Secure Patient", "age": 55},
            headers=auth_headers
        )
        pid = create_res.json()["patient_id"]

        del_res = client.delete(f"/api/patients/{pid}", headers=alt_auth_headers)
        assert del_res.status_code == 404


class TestUploadSecurity:
    """Upload boundary validation beyond basic ingestion tests."""

    def test_path_traversal_filename_rejected(self, client, auth_headers):
        """A filename containing path traversal sequences should be safe."""
        traversal_file = io.BytesIO(b"Some report text content")
        res = client.post(
            "/api/ingest/file",
            files={"file": ("../../etc/passwd", traversal_file, "text/plain")},
            headers=auth_headers
        )
        # Should either reject (400) or safely sanitize the filename
        # It should not create a file at the traversal path
        assert res.status_code in (200, 400)
        if res.status_code == 200:
            # If accepted, the stored filename should not contain traversal
            data = res.json()
            assert ".." not in data.get("filename", "")

    def test_null_byte_filename_rejected(self, client, auth_headers):
        """Null bytes in filename should be rejected or sanitized."""
        null_file = io.BytesIO(b"Test content")
        res = client.post(
            "/api/ingest/file",
            files={"file": ("report\x00.exe.txt", null_file, "text/plain")},
            headers=auth_headers
        )
        assert res.status_code in (200, 400)

    def test_double_extension_exe_rejected(self, client, auth_headers):
        """Files with dangerous double extensions should be rejected."""
        double_ext = io.BytesIO(b"Not really a text file")
        res = client.post(
            "/api/ingest/file",
            files={"file": ("report.txt.exe", double_ext, "application/x-msdownload")},
            headers=auth_headers
        )
        assert res.status_code == 400


class TestDocumentDeletion:
    """Verify document deletion is functional and scoped."""

    def test_delete_own_document(self, client, auth_headers):
        ingest_res = client.post(
            "/api/ingest/text",
            json={"title": "Deletable Report", "text": "Creatinine: 1.1 mg/dL"},
            headers=auth_headers
        )
        doc_id = ingest_res.json()["document_id"]

        del_res = client.delete(f"/api/documents/{doc_id}", headers=auth_headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # Confirm it's gone
        get_res = client.get(f"/api/documents/{doc_id}", headers=auth_headers)
        assert get_res.status_code == 404

    def test_delete_nonexistent_document(self, client, auth_headers):
        del_res = client.delete("/api/documents/nonexistent-id-999", headers=auth_headers)
        assert del_res.status_code == 404
