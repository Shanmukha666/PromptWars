"""
Ingestion Service: Upload validation, collision-safe file handling, and document persistence.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import UploadFile

from backend.config import settings
from backend.exceptions import (
    UnsupportedFileTypeError,
    FileTooLargeError,
    MagicBytesMismatchError,
    EmptyDocumentError,
    DocumentExtractionError,
)
from backend.repositories.report_repository import ReportRepository
from backend.services.extraction_service import ExtractionService
from backend.services.summary_service import SummaryService
from backend.llm.client import GeminiClient
from services.parser import get_parser_service

logger = logging.getLogger("medlens.ingestion")


class IngestionService:
    def __init__(
        self,
        report_repo: ReportRepository,
        extraction_service: ExtractionService,
        summary_service: SummaryService,
        llm: GeminiClient,
    ):
        self.report_repo = report_repo
        self.extraction_service = extraction_service
        self.summary_service = summary_service
        self.llm = llm
        self.parser = get_parser_service()

    async def ingest_file(
        self,
        upload: UploadFile,
        title: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not upload.filename or not upload.filename.strip():
            raise UnsupportedFileTypeError("empty_filename", settings.ALLOWED_EXTENSIONS)

        suffix = Path(upload.filename).suffix.lower()
        if suffix not in settings.ALLOWED_EXTENSIONS:
            raise UnsupportedFileTypeError(suffix, settings.ALLOWED_EXTENSIONS)

        content = await upload.read()
        if not content or len(content.strip()) == 0:
            raise EmptyDocumentError()
        if len(content) > settings.MAX_UPLOAD_BYTES:
            raise FileTooLargeError(len(content), settings.MAX_UPLOAD_BYTES)

        if suffix in settings.MAGIC_SIGNATURES:
            sig = settings.MAGIC_SIGNATURES[suffix]
            if not content.startswith(sig):
                raise MagicBytesMismatchError(suffix)

        file_uuid = uuid.uuid4().hex
        file_path = settings.UPLOAD_DIR / f"upload_{file_uuid}{suffix}"

        try:
            file_path.write_bytes(content)
            parsed = await self.parser.parse(str(file_path))
            text = (parsed.text or "").strip()
            if not text:
                raise DocumentExtractionError()

            clean_title = (title or Path(upload.filename).name or "Uploaded report")[:120]
            return self.persist_document(
                patient_id=patient_id,
                session_id=session_id,
                title=clean_title,
                source_type=parsed.format,
                source_name=Path(upload.filename).name[:100],
                raw_text=text,
                metadata=parsed.metadata,
                tables=parsed.tables,
            )
        except (UnsupportedFileTypeError, FileTooLargeError, MagicBytesMismatchError, EmptyDocumentError, DocumentExtractionError):
            raise
        except Exception as exc:
            logger.error("Failed to parse document: %s", type(exc).__name__)
            raise DocumentExtractionError("Document parser could not process the provided file safely.")

    async def ingest_text(
        self,
        text: str,
        title: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise EmptyDocumentError("Text input is empty.")
        return self.persist_document(
            patient_id=patient_id,
            session_id=session_id,
            title=(title or "Pasted text")[:120],
            source_type="text",
            source_name=None,
            raw_text=clean,
            metadata={"characters": len(clean), "words": len(clean.split())},
            tables=[],
        )

    def persist_document(
        self,
        *,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        title: str,
        source_type: str,
        source_name: Optional[str],
        raw_text: str,
        metadata: Dict[str, Any],
        tables: list,
    ) -> Dict[str, Any]:
        if self.llm.configured:
            try:
                extracted = self.llm.extract_clinical_data(raw_text)
            except Exception as e:
                logger.warning("LLM extraction failed (%s), falling back to deterministic extractor", type(e).__name__)
                extracted = {
                    "labs": self.extraction_service.extract_labs(raw_text),
                    "entities": self.extraction_service.extract_entities(raw_text),
                }
        else:
            extracted = {
                "labs": self.extraction_service.extract_labs(raw_text),
                "entities": self.extraction_service.extract_entities(raw_text),
            }

        cleaned_labs = {}
        for test_key, item in extracted.get("labs", {}).items():
            if not isinstance(item, dict):
                continue
            raw_range = item.get("reference_range_raw") or item.get("source_range_raw")
            ref = item.get("reference_range")
            cleaned_labs[test_key] = {
                "test_name": item.get("test_name", test_key),
                "display_name": item.get("display_name", test_key.capitalize()),
                "value": item.get("value"),
                "unit": str(item.get("unit") or "").strip(),
                "reference_range_raw": raw_range,
                "reference_range_low": item.get("reference_range_low"),
                "reference_range_high": item.get("reference_range_high"),
                "reference_range_operator": item.get("reference_range_operator"),
                "reference_range": ref,
                "source_range_raw": raw_range,
                "parsed_min": item.get("parsed_min") or (ref.get("min") if isinstance(ref, dict) else None),
                "parsed_max": item.get("parsed_max") or (ref.get("max") if isinstance(ref, dict) else None),
                "reference_range_text": item.get("reference_range_text") or ("Reference range not available in source report." if not raw_range else f"Source reference: {raw_range}"),
                "status": item.get("status", "not_assessed"),
                "needs_review": item.get("needs_review", False),
                "source_flag": item.get("source_flag"),
                "observation_date": item.get("observation_date"),
                "source_page": item.get("source_page", 1),
                "source_snippet": item.get("source_snippet") or (raw_text[:120] if raw_text else ""),
                "extraction_confidence": item.get("extraction_confidence", 0.95 if raw_range else 0.85),
                "verification_status": item.get("verification_status", "unverified"),
                "provenance_type": item.get("provenance_type", "source_extracted"),
            }
        extracted["labs"] = cleaned_labs
        extracted["tables"] = tables[:5]
        extracted["sections"] = self.extraction_service.extract_sections(raw_text)
        ai_summary = self.summary_service.build_summary(
            title=title, raw_text=raw_text, metadata=metadata, extracted=extracted
        )
        return self.report_repo.upsert_document(
            patient_id=patient_id,
            session_id=session_id,
            title=title,
            source_type=source_type,
            source_name=source_name,
            raw_text=raw_text,
            metadata={**metadata, "words": len(raw_text.split()), "characters": len(raw_text)},
            extracted=extracted,
            ai_summary=ai_summary,
        )
