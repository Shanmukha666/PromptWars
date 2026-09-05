import io
import time
import unittest
from fastapi.testclient import TestClient
from backend.app import app
from backend.api.dependencies import get_report_repo

client = TestClient(app)


class TestPerformanceAndResourceUsage(unittest.TestCase):
    """
    Performance profiling and resource consumption test suite for MedLens.
    """

    @classmethod
    def setUpClass(cls):
        # Ingest a sample clinical document to ensure search index is populated
        cls.session_id = "perf-test-session"
        res = client.post(
            "/api/ingest/text",
            json={
                "title": "Comprehensive Metabolic Report",
                "text": (
                    "METRO GENERAL HOSPITAL\n"
                    "Patient: Benchmark Test Subject\n"
                    "Hemoglobin: 13.5 g/dL (Ref: 12.0 - 16.0 g/dL)\n"
                    "Platelets: 240 x10^3/uL (Ref: 150 - 450 x10^3/uL)\n"
                    "WBC: 7.2 x10^3/uL (Ref: 4.5 - 11.0 x10^3/uL)\n"
                    "Glucose: 98 mg/dL (Ref: 70 - 99 mg/dL)\n"
                    "Creatinine: 0.9 mg/dL (Ref: 0.6 - 1.2 mg/dL)\n"
                    "BUN: 14 mg/dL (Ref: 7 - 20 mg/dL)\n"
                    "Sodium: 140 mmol/L (Ref: 136 - 145 mmol/L)\n"
                    "Potassium: 4.2 mmol/L (Ref: 3.5 - 5.1 mmol/L)\n"
                    "Calcium: 9.4 mg/dL (Ref: 8.5 - 10.2 mg/dL)\n"
                    "Total Protein: 7.1 g/dL (Ref: 6.0 - 8.3 g/dL)\n"
                    "Bilirubin: 0.8 mg/dL (Ref: 0.2 - 1.2 mg/dL)\n"
                    "ALP: 75 U/L (Ref: 44 - 147 U/L)\n"
                    "AST: 22 U/L (Ref: 10 - 40 U/L)\n"
                    "ALT: 28 U/L (Ref: 7 - 56 U/L)\n"
                )
            },
            headers={"X-Session-ID": cls.session_id}
        )
        assert res.status_code == 200
        cls.doc_id = res.json()["document_id"]

    def test_in_memory_search_index_caching_speed(self):
        """
        Verify that repeated search queries execute in-memory with sub-millisecond to low millisecond latency,
        avoiding repeated disk deserialization via joblib.load().
        """
        repo = get_report_repo()
        
        # Warmup search
        repo.search("hemoglobin platelets glucose", limit=5, session_id=self.session_id)

        # Measure repeated in-memory searches
        latencies = []
        iterations = 50
        for _ in range(iterations):
            start = time.perf_counter()
            results = repo.search("hemoglobin platelets glucose", limit=5, session_id=self.session_id)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            latencies.append(elapsed)
            self.assertTrue(len(results) > 0)

        avg_latency = sum(latencies) / len(latencies)
        # Average in-memory search must execute in under 15ms (typically < 3ms)
        self.assertLess(avg_latency, 15.0, f"Average in-memory search took {avg_latency:.2f}ms, expected < 15ms")

    def test_streaming_upload_rejects_oversized_file_midstream(self):
        """
        Verify that streaming file upload aborts early without holding the full oversized payload in memory.
        """
        # 11MB file
        oversized = io.BytesIO(b"A" * (11 * 1024 * 1024))
        res = client.post(
            "/api/ingest/file",
            files={"file": ("stream_large.txt", oversized, "text/plain")},
            headers={"X-Session-ID": self.session_id}
        )
        self.assertEqual(res.status_code, 413)

    def test_document_listing_pagination(self):
        """
        Verify that /api/documents supports limit and offset pagination.
        """
        res = client.get(
            "/api/documents?limit=1&offset=0",
            headers={"X-Session-ID": self.session_id}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("items", data)
        self.assertIn("limit", data)
        self.assertIn("offset", data)
        self.assertEqual(data["limit"], 1)
        self.assertEqual(data["offset"], 0)
        self.assertLessEqual(len(data["items"]), 1)

    def test_document_lazy_loading_chunks(self):
        """
        Verify that get_document with include_chunks=False omits chunk array to minimize payload transfer.
        """
        # 1. Fetch with chunks
        res_with = client.get(
            f"/api/documents/{self.doc_id}?include_chunks=true",
            headers={"X-Session-ID": self.session_id}
        )
        self.assertEqual(res_with.status_code, 200)
        chunks_with = res_with.json().get("chunks", [])
        self.assertTrue(len(chunks_with) > 0)

        # 2. Fetch without chunks (lazy-loaded / light payload)
        res_without = client.get(
            f"/api/documents/{self.doc_id}?include_chunks=false",
            headers={"X-Session-ID": self.session_id}
        )
        self.assertEqual(res_without.status_code, 200)
        chunks_without = res_without.json().get("chunks", [])
        self.assertEqual(len(chunks_without), 0)


if __name__ == "__main__":
    unittest.main()
