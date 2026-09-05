"""
Backward-compatibility facade for MedLens simple_api.
Exposes app, Analyzer, and legacy helper signatures used by existing test suites.
"""

from typing import Any, Dict, List, Optional
from fastapi import UploadFile

from backend.app import app
from backend.config import settings, UPLOAD_DIR, INDEX_DIR
from backend.api.dependencies import (
    patient_repo,
    report_repo,
    llm_client,
    extraction_service,
    summary_service,
    provenance_service,
    comparison_service,
    ingestion_service,
)
from backend.api.schemas import (
    PatientCreateRequest as PatientCreate,
    PatientUpdateRequest as PatientUpdate,
    LabUpdateRequest,
    IngestTextRequest,
    AskRequest,
    SearchRequest,
    PipelineRequest,
    MultiAgentRequest,
)

ALLOWED_ORIGINS = settings.cors_allowed_origins
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS


class Analyzer:
    """
    Facade maintaining Analyzer interface for existing tests and consumers.
    Delegates to clean domain services and repositories.
    """
    def __init__(self):
        self.store = report_repo
        self.llm = llm_client
        self.parser = ingestion_service.parser
        self.extraction_service = extraction_service
        self.summary_service = summary_service
        self.provenance_service = provenance_service
        self.comparison_service = comparison_service
        self.ingestion_service = ingestion_service

    async def ingest_file(
        self,
        upload: UploadFile,
        title: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.ingestion_service.ingest_file(upload, title, patient_id, session_id)

    async def ingest_text(
        self,
        text: str,
        title: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.ingestion_service.ingest_text(text, title, patient_id, session_id)

    def _persist_document(self, **kwargs) -> Dict[str, Any]:
        return self.ingestion_service.persist_document(**kwargs)

    def _extract_labs(self, text: str) -> Dict[str, Any]:
        return self.extraction_service.extract_labs(text)

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        return self.extraction_service.extract_entities(text)

    def _extract_sections(self, text: str) -> Dict[str, str]:
        return self.extraction_service.extract_sections(text)

    def _fallback_document_summary(
        self,
        title: str,
        raw_text: str,
        extracted: Dict[str, Any],
        review_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.summary_service.fallback_summary(title, raw_text, extracted, review_reason)

    def _audit_reference_ranges(self, labs: Dict[str, Any]) -> Dict[str, Any]:
        return self.comparison_service.audit_reference_ranges(labs)

    def _corroborate_clinical_context(
        self,
        labs: Dict[str, Any],
        entities: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return self.comparison_service.corroborate_clinical_context(labs, entities, chunks)

    def get_processing_pipeline(
        self,
        document_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.provenance_service.get_pipeline(document_id, session_id)

    def semantic_search(
        self,
        query: str,
        document_id: Optional[str],
        top_k: int,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        results = self.store.search(query=query, limit=top_k, document_id=document_id, session_id=session_id)
        return {"query": query, "count": len(results), "results": results}

    def answer_question(
        self,
        question: str,
        document_id: Optional[str],
        top_k: int,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        chunks = self.store.search(query=question, limit=top_k, document_id=document_id, session_id=session_id)
        doc = self.store.get_document(document_id, session_id=session_id) if document_id else None
        title = doc["title"] if doc else None
        if self.llm.configured:
            try:
                return self.llm.answer_with_context(question=question, context_chunks=chunks, document_title=title)
            except Exception:
                pass
        snippet = chunks[0]["text"][:300] if chunks else "No relevant document excerpt identified."
        return {
            "answer": f"Based on the clinical record: {snippet}",
            "citations": [{"chunk": 1, "text": snippet[:100]}],
            "follow_up_questions": ["What reference ranges are provided in the source report?"],
            "processing_mode": "offline-local"
        }


analyzer = Analyzer()
