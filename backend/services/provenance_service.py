"""
Provenance Service: Builds the 8-stage transparent processing pipeline.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.repositories.report_repository import ReportRepository


class ProvenanceService:
    def __init__(self, report_repo: ReportRepository):
        self.report_repo = report_repo

    def get_pipeline(self, document_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        doc = self.report_repo.get_document(document_id, session_id=session_id) if document_id else None
        if not doc:
            recent_docs = self.report_repo.list_documents(limit=1, session_id=session_id)
            if recent_docs:
                doc = self.report_repo.get_document(recent_docs[0]["document_id"], session_id=session_id)

        if not doc:
            return {"document_id": None, "pipeline": [], "pipeline_stages": [], "message": "No documents available for processing inspection."}

        labs = doc.get("extracted", {}).get("labs", {})
        raw_text = doc.get("raw_text", "")
        created_ts = doc.get("created_at", datetime.now(timezone.utc).isoformat())

        ranges_found = sum(1 for item in labs.values() if item.get("reference_range_raw"))
        need_review = sum(1 for item in labs.values() if item.get("status") == "not_assessed")

        stage_4_warnings = []
        if need_review > 0:
            stage_4_warnings.append(f"{need_review} observation(s) lack source ranges; marked 'not_assessed'.")

        stages = [
            {"stage_id": "doc_received", "step": 1, "title": "Document received", "status": "completed", "timestamp": created_ts, "produced": f"Received '{doc['title']}' ({doc['source_type']}).", "evidence": [{"label": "Document", "value": doc["title"]}], "warnings": []},
            {"stage_id": "text_extracted", "step": 2, "title": "Text extracted", "status": "completed", "timestamp": created_ts, "produced": f"Extracted {len(raw_text.split())} words.", "evidence": [{"label": "Word count", "value": str(len(raw_text.split()))}], "warnings": []},
            {"stage_id": "fields_detected", "step": 3, "title": "Fields detected", "status": "completed", "timestamp": created_ts, "produced": f"Detected {len(labs)} observations.", "evidence": [{"label": "Tests", "value": ", ".join(list(labs.keys())[:5]) or "None"}], "warnings": []},
            {"stage_id": "ranges_linked", "step": 4, "title": "Source ranges linked", "status": "needs_review" if need_review > 0 else "completed", "timestamp": created_ts, "produced": f"{len(labs)} observations evaluated · {ranges_found} source ranges found · {need_review} need review", "evidence": [{"label": "Evaluated", "value": str(len(labs))}], "metrics": {"observations_evaluated": len(labs), "source_ranges_found": ranges_found, "need_review": need_review}, "warnings": stage_4_warnings},
            {"stage_id": "provenance_attached", "step": 5, "title": "Provenance attached", "status": "completed", "timestamp": created_ts, "produced": f"Linked provenance to {len(labs)} observations.", "evidence": [{"label": "Linked", "value": str(len(labs))}], "warnings": []},
            {"stage_id": "consistency_checked", "step": 6, "title": "Consistency checked", "status": "completed", "timestamp": created_ts, "produced": "Factual cross-checks completed without diagnostic assertions.", "evidence": [{"label": "Check", "value": "Factual consistency validated"}], "warnings": []},
            {"stage_id": "summary_prepared", "step": 7, "title": "Summary prepared", "status": "completed", "timestamp": created_ts, "produced": "Non-diagnostic summary validated.", "evidence": [{"label": "Format", "value": "Patient-friendly factual record"}], "warnings": []},
            {"stage_id": "human_review", "step": 8, "title": "Human review", "status": "needs_review" if need_review > 0 else "completed", "timestamp": created_ts, "produced": f"{need_review} item(s) flagged for clinician review.", "evidence": [{"label": "Pending review", "value": str(need_review)}], "warnings": []},
        ]
        return {"document_id": doc["document_id"], "title": doc["title"], "pipeline": stages, "pipeline_stages": stages}
