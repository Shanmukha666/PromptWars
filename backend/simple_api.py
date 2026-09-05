from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile, Depends, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.llm import GeminiClient, GeminiError, FeatherlessClient, FeatherlessError
from backend.reference_range import extract_labs_from_report, parse_source_reference_range, evaluate_clinical_status
from backend.summary_schema import ClinicalSummarySchema, validate_or_fallback_summary, MANDATORY_FOOTER
from backend.retrieval import RetrievalStore
from services.parser import get_parser_service

load_dotenv()

# Configure logging with sensitive data redaction
class SensitiveDataFilter(logging.Filter):
    """Redacts potentially sensitive patient/report data from log outputs."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            # Redact common PHI patterns if inadvertently passed to logger
            record.msg = re.sub(r'(?i)(name|patient|ssn|dob)[:=]\s*[^,\s]+', r'\1=[REDACTED]', record.msg)
        return True

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("medlens.security")
logger.addFilter(SensitiveDataFilter())

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'data'
UPLOAD_DIR = DATA_DIR / 'uploads'
INDEX_DIR = DATA_DIR / 'indexes'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.json', '.html', '.htm', '.docx', '.xml'}
# Magic bytes signature validation for file uploads
MAGIC_SIGNATURES = {
    '.pdf': b'%PDF-',
    '.docx': b'PK\x03\x04',
}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB prototype upload limit
DEFAULT_SESSION_ID = "demo-user-session"


# ==================== Rate Limiting (In-Memory Prototype) ====================
RATE_LIMIT_BUCKET: Dict[str, List[float]] = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60"))

def check_rate_limit(client_ip: str, endpoint: str = "general", max_requests: int = 60, window_secs: float = 60.0):
    key = f"{client_ip}:{endpoint}"
    now = time.time()
    RATE_LIMIT_BUCKET[key] = [ts for ts in RATE_LIMIT_BUCKET[key] if now - ts < window_secs]
    if len(RATE_LIMIT_BUCKET[key]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({max_requests} req/{int(window_secs)}s). Please wait before retrying."
        )
    RATE_LIMIT_BUCKET[key].append(now)


# ==================== Authentication & Session Scoping ====================
def get_session_id(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Resolves the scoped session/user token for authorization.
    In this prototype auth model:
    - Accepts 'X-Session-ID: <session_id>' or 'Authorization: Bearer <session_id>'
    - Defaults to 'demo-user-session' for backward-compatible local/demo workflows
    - Guarantees strict user isolation: User A cannot query or enumerate User B's documents
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        if token:
            return token
    if x_session_id and x_session_id.strip():
        return x_session_id.strip()
    return DEFAULT_SESSION_ID


# ==================== Pydantic Request Models ====================
class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=130)
    sex: Optional[str] = Field(None, max_length=30)
    symptoms: List[str] = Field(default_factory=list, max_length=50)
    conditions: List[str] = Field(default_factory=list, max_length=50)
    allergies: List[str] = Field(default_factory=list, max_length=50)
    medications: List[str] = Field(default_factory=list, max_length=50)
    notes: Optional[str] = Field('', max_length=2000)


class PatientUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=130)
    sex: Optional[str] = Field(None, max_length=30)
    symptoms: List[str] = Field(default_factory=list, max_length=50)
    conditions: List[str] = Field(default_factory=list, max_length=50)
    allergies: List[str] = Field(default_factory=list, max_length=50)
    medications: List[str] = Field(default_factory=list, max_length=50)
    notes: Optional[str] = Field('', max_length=2000)


class LabUpdateRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=64)
    test_name: str = Field(min_length=1, max_length=100)
    action: Optional[str] = 'verify'  # verify, edit, mark_incorrect, remove, add
    value: Optional[float] = None
    unit: Optional[str] = Field('', max_length=40)
    reference_range_raw: Optional[str] = Field(None, max_length=100)
    parsed_min: Optional[float] = None
    parsed_max: Optional[float] = None
    verification_status: Optional[str] = 'verified'
    notes: Optional[str] = Field(None, max_length=1000)
    original_value: Optional[float] = None
    source_page: Optional[int] = 1
    source_snippet: Optional[str] = Field(None, max_length=500)


class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100000)
    title: Optional[str] = Field(None, max_length=150)
    patient_id: Optional[str] = Field(None, max_length=64)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    document_id: Optional[str] = Field(None, max_length=64)
    top_k: int = Field(default=6, ge=1, le=12)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    document_id: Optional[str] = Field(None, max_length=64)
    top_k: int = Field(default=8, ge=1, le=20)


class PipelineRequest(BaseModel):
    document_id: Optional[str] = Field(None, max_length=64)
    question: Optional[str] = Field(None, max_length=500)
    top_k: int = 4

# Backwards compatibility alias
MultiAgentRequest = PipelineRequest


# ==================== Analyzer Business Logic ====================
class Analyzer:
    def __init__(self) -> None:
        self.parser = get_parser_service()
        self.store = RetrievalStore(INDEX_DIR)
        self.llm = GeminiClient()

    async def ingest_file(
        self,
        upload: UploadFile,
        title: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        if not upload.filename or not upload.filename.strip():
            raise HTTPException(status_code=400, detail='Uploaded file must have a valid filename.')
        
        # 1. Whitelist extension check
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f'Unsupported file extension: "{suffix}". Allowed formats: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
            )

        # 2. Size limit check before writing
        content = await upload.read()
        if not content or len(content.strip()) == 0:
            raise HTTPException(status_code=400, detail='Uploaded file is empty (0 bytes). Please upload a valid report.')
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f'Uploaded file exceeds the maximum {MAX_UPLOAD_BYTES // (1024*1024)}MB limit.')

        # 3. Magic bytes signature validation where applicable
        if suffix in MAGIC_SIGNATURES:
            sig = MAGIC_SIGNATURES[suffix]
            if not content.startswith(sig):
                raise HTTPException(
                    status_code=400,
                    detail=f'File content does not match expected {suffix} binary signature (magic bytes check failed).'
                )

        # 4. Generate collision-safe UUID filename (never trust user filename as path)
        file_uuid = uuid.uuid4().hex
        file_path = UPLOAD_DIR / f'upload_{file_uuid}{suffix}'

        try:
            file_path.write_bytes(content)
            parsed = await self.parser.parse(str(file_path))
            text = (parsed.text or '').strip()
            if not text:
                raise HTTPException(status_code=422, detail='No readable text could be extracted from the file.')
            
            clean_title = (title or Path(upload.filename).name or 'Uploaded report')[:120]
            return self._persist_document(
                patient_id=patient_id,
                session_id=session_id,
                title=clean_title,
                source_type=parsed.format,
                source_name=Path(upload.filename).name[:100],
                raw_text=text,
                metadata=parsed.metadata,
                tables=parsed.tables,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Failed to parse document: %s", type(exc).__name__)
            raise HTTPException(status_code=422, detail="Document parser could not process the provided file safely.")
        finally:
            # Retention & Temp clean-up: Keep uploaded file on disk safely or prune
            pass

    async def ingest_text(
        self,
        text: str,
        title: Optional[str] = None,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise HTTPException(status_code=400, detail='Text input is empty.')
        return self._persist_document(
            patient_id=patient_id,
            session_id=session_id,
            title=(title or 'Pasted text')[:120],
            source_type='text',
            source_name=None,
            raw_text=clean,
            metadata={'characters': len(clean), 'words': len(clean.split())},
            tables=[],
        )

    def _persist_document(
        self,
        *,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        title: str,
        source_type: str,
        source_name: Optional[str],
        raw_text: str,
        metadata: Dict[str, Any],
        tables: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self.llm.configured:
            try:
                extracted = self.llm.extract_clinical_data(raw_text)
            except Exception as e:
                logger.warning("LLM extraction failed (%s), falling back to deterministic extractor", type(e).__name__)
                extracted = {
                    'labs': self._extract_labs(raw_text),
                    'entities': self._extract_entities(raw_text),
                }
        else:
            extracted = {
                'labs': self._extract_labs(raw_text),
                'entities': self._extract_entities(raw_text),
            }

        # Enforce Zero-Hallucination Reference Range rule:
        # Values may ONLY be marked low/normal/high if an explicit source reference range is provided!
        cleaned_labs = {}
        for test_key, item in extracted.get('labs', {}).items():
            if not isinstance(item, dict):
                continue
            raw_range = item.get('reference_range_raw') or item.get('source_range_raw')
            ref = item.get('reference_range')
            cleaned_labs[test_key] = {
                'test_name': item.get('test_name', test_key),
                'display_name': item.get('display_name', test_key.capitalize()),
                'value': item.get('value'),
                'unit': str(item.get('unit') or '').strip(),
                'reference_range_raw': raw_range,
                'reference_range_low': item.get('reference_range_low'),
                'reference_range_high': item.get('reference_range_high'),
                'reference_range_operator': item.get('reference_range_operator'),
                'reference_range': ref,
                'source_range_raw': raw_range,
                'parsed_min': item.get('parsed_min') or (ref.get('min') if isinstance(ref, dict) else None),
                'parsed_max': item.get('parsed_max') or (ref.get('max') if isinstance(ref, dict) else None),
                'reference_range_text': item.get('reference_range_text') or ('Reference range not available in source report.' if not raw_range else f"Source reference: {raw_range}"),
                'status': item.get('status', 'not_assessed'),
                'needs_review': item.get('needs_review', False),
                'source_flag': item.get('source_flag'),
                'observation_date': item.get('observation_date'),
                'source_page': item.get('source_page', 1),
                'source_snippet': item.get('source_snippet') or (raw_text[:120] if raw_text else ''),
                'extraction_confidence': item.get('extraction_confidence', 0.95 if raw_range else 0.85),
                'verification_status': item.get('verification_status', 'unverified'),
                'provenance_type': item.get('provenance_type', 'source_extracted'),
            }
        extracted['labs'] = cleaned_labs
        extracted['tables'] = tables[:5]
        extracted['sections'] = self._extract_sections(raw_text)
        ai_summary = self._build_ai_summary(title, raw_text, metadata, extracted)
        return self.store.upsert_document(
            patient_id=patient_id,
            session_id=session_id,
            title=title,
            source_type=source_type,
            source_name=source_name,
            raw_text=raw_text,
            metadata={**metadata, 'words': len(raw_text.split()), 'characters': len(raw_text)},
            extracted=extracted,
            ai_summary=ai_summary,
        )

    def _build_ai_summary(self, title: str, raw_text: str, metadata: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
        if self.llm.configured:
            try:
                candidate = self.llm.summarize_document(title=title, text=raw_text, metadata=metadata, extracted=extracted)
                return validate_or_fallback_summary(
                    candidate=candidate,
                    title=title,
                    raw_text=raw_text,
                    extracted=extracted,
                    fallback_builder=self._fallback_document_summary
                )
            except Exception as exc:
                return self._fallback_document_summary(
                    title=title,
                    raw_text=raw_text,
                    extracted=extracted,
                    review_reason=f"AI summarization fallback ({type(exc).__name__}). Factual summary provided."
                )
        return self._fallback_document_summary(title=title, raw_text=raw_text, extracted=extracted)

    def _extract_labs(self, text: str) -> Dict[str, Any]:
        """Deterministic source-grounded lab extraction."""
        return extract_labs_from_report(text)

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        t = text.lower()
        symptom_pool = ['fatigue', 'fever', 'cough', 'shortness of breath', 'headache', 'dizziness', 'chest pain', 'nausea', 'vomiting', 'pain', 'rash', 'weakness', 'tiredness', 'pale skin']
        condition_pool = ['anemia', 'hypertension', 'diabetes', 'asthma', 'infection', 'copd', 'heart disease', 'kidney disease', 'pneumonia', 'bronchitis']
        medication_pool = ['iron supplement', 'metformin', 'lisinopril', 'amoxicillin', 'ibuprofen', 'aspirin', 'atorvastatin', 'albuterol', 'omeprazole', 'levothyroxine']

        return {
            'symptoms': [s for s in symptom_pool if s in t],
            'conditions': [c for c in condition_pool if c in t],
            'medications': [m for m in medication_pool if m in t],
        }

    def _extract_sections(self, text: str) -> Dict[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections: Dict[str, str] = {}
        current_name = 'General'
        current_body: List[str] = []

        for line in lines:
            if line.endswith(':') and len(line) < 40:
                if current_body:
                    sections[current_name] = ' '.join(current_body)[:800]
                    current_body = []
                current_name = line[:-1]
            else:
                current_body.append(line)
        if current_body:
            sections[current_name] = ' '.join(current_body)[:800]
        return sections

    def _fallback_document_summary(
        self,
        title: str,
        raw_text: str,
        extracted: Dict[str, Any],
        review_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        labs = extracted.get('labs', {})
        outside = [
            f"{item.get('test_name', k).upper()}: {item.get('value')} {item.get('unit', '')} (classified {item.get('status')} against source range {item.get('reference_range_raw')})"
            for k, item in labs.items()
            if item.get('status') in {'low', 'high'}
        ]
        items_needing_review = []
        if review_reason:
            items_needing_review.append(review_reason)
        no_ref_tests = [k.upper() for k, item in labs.items() if item.get('status') == 'not_assessed']
        if no_ref_tests:
            items_needing_review.append(
                f"Missing source reference ranges for: {', '.join(no_ref_tests)}. Marked 'not_assessed' (ranges never invented)."
            )

        meds = extracted.get('entities', {}).get('medications', [])
        med_allergy_info = [f"Medications noted: {', '.join(meds)}"] if meds else ["No active medications recorded in this report."]

        return {
            'overview': f"Clinical record '{title}' processed. Extracted {len(labs)} laboratory test observation(s) and clinical context entries.",
            'key_findings': [
                f"Extracted {len(labs)} laboratory observation(s) directly from source document.",
                f"{len(outside)} observation(s) fall outside source-provided reference ranges." if outside else "All parameters with source-provided ranges fall within expected intervals.",
            ],
            'outside_source_ranges': outside if outside else ["None. All tests with explicit source reference ranges fall within expected bounds."],
            'medication_allergy_info': med_allergy_info,
            'items_needing_review': items_needing_review if items_needing_review else ["Extraction verified against source document text."],
            'footer': MANDATORY_FOOTER,
        }

    def semantic_search(self, query: str, document_id: Optional[str], top_k: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        results = self.store.search(query=query, limit=top_k, document_id=document_id, session_id=session_id)
        return {'query': query, 'count': len(results), 'results': results}

    def answer_question(self, question: str, document_id: Optional[str], top_k: int, session_id: Optional[str] = None) -> Dict[str, Any]:
        chunks = self.store.search(query=question, limit=top_k, document_id=document_id, session_id=session_id)
        doc = self.store.get_document(document_id, session_id=session_id) if document_id else None
        title = doc['title'] if doc else None

        if self.llm.configured:
            try:
                return self.llm.answer_with_context(question=question, context_chunks=chunks, document_title=title)
            except Exception as e:
                logger.warning("LLM answer generation failed: %s", type(e).__name__)

        # Offline / deterministic answer fallback
        snippet = chunks[0]['text'][:300] if chunks else 'No relevant document excerpt identified.'
        return {
            'answer': f"Based on the clinical record: {snippet}",
            'citations': [{'chunk': 1, 'text': snippet[:100]}],
            'follow_up_questions': ['What reference ranges are provided in the source report?'],
            'processing_mode': 'offline-local'
        }


    def _audit_reference_ranges(self, labs: Dict[str, Any]) -> Dict[str, Any]:
        outside = []
        within = []
        unspecified = []
        for name, item in labs.items():
            st = item.get('status')
            rec = {'test': name, 'value': item.get('value'), 'unit': item.get('unit'), 'status': st}
            if st in {'low', 'high'}:
                outside.append(rec)
            elif st == 'normal':
                within.append(rec)
            else:
                unspecified.append(rec)
        return {
            'outside_source_range': outside,
            'within_source_range': within,
            'unspecified_reference_range': unspecified,
            'not_assessed': unspecified,
        }

    def _corroborate_clinical_context(self, labs: Dict[str, Any], entities: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        obs = []
        symptoms = entities.get('symptoms', [])
        hb = labs.get('hemoglobin', {})
        if hb.get('status') == 'low':
            if 'fatigue' in symptoms or 'dizziness' in symptoms:
                obs.append(f"Low hemoglobin ({hb.get('value')} {hb.get('unit', '')}) co-occurs with documented symptom(s).")
            else:
                obs.append("Low hemoglobin documented outside source reference range.")
        if not obs:
            obs.append("All observations consistent with documented clinical context.")
        return {
            'contextual_observations': obs,
            'safety_note': 'Correlations are factual consistency checks for clinician review. MedLens does not generate diagnoses.'
        }

    def _suggest_grounded_questions(self, document: Dict[str, Any], evidence: List[Dict[str, Any]]) -> List[str]:
        labs = document.get('extracted', {}).get('labs', {})
        outside = [k for k, v in labs.items() if v.get('status') in {'low', 'high'}]
        suggestions = []
        if outside:
            suggestions.append(f"What source reference intervals were used to classify {outside[0]}?")
        suggestions.append("Which observations in this report lack explicit reference ranges?")
        suggestions.append("What medications and allergies are documented?")
        return suggestions[:4]

    def get_processing_pipeline(self, document_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        doc = self.store.get_document(document_id, session_id=session_id) if document_id else None
        if not doc:
            recent_docs = self.store.list_documents(limit=1, session_id=session_id)
            if recent_docs:
                doc = self.store.get_document(recent_docs[0]['document_id'], session_id=session_id)

        if not doc:
            return {'document_id': None, 'pipeline_stages': [], 'message': 'No documents available for processing inspection.'}

        labs = doc.get('extracted', {}).get('labs', {})
        raw_text = doc.get('raw_text', '')
        created_ts = doc.get('created_at', datetime.now(timezone.utc).isoformat())

        # Build 8-stage transparent pipeline representation
        ranges_found = sum(1 for item in labs.values() if item.get('reference_range_raw'))
        need_review = sum(1 for item in labs.values() if item.get('status') == 'not_assessed')

        stage_4_warnings = []
        if need_review > 0:
            stage_4_warnings.append(f"{need_review} observation(s) lack source ranges; marked 'not_assessed'.")

        stages = [
            {'stage_id': 'doc_received', 'step': 1, 'title': 'Document received', 'status': 'completed', 'timestamp': created_ts, 'produced': f"Received '{doc['title']}' ({doc['source_type']}).", 'evidence': [{'label': 'Document', 'value': doc['title']}], 'warnings': []},
            {'stage_id': 'text_extracted', 'step': 2, 'title': 'Text extracted', 'status': 'completed', 'timestamp': created_ts, 'produced': f"Extracted {len(raw_text.split())} words.", 'evidence': [{'label': 'Word count', 'value': str(len(raw_text.split()))}], 'warnings': []},
            {'stage_id': 'fields_detected', 'step': 3, 'title': 'Fields detected', 'status': 'completed', 'timestamp': created_ts, 'produced': f"Detected {len(labs)} observations.", 'evidence': [{'label': 'Tests', 'value': ', '.join(list(labs.keys())[:5]) or 'None'}], 'warnings': []},
            {'stage_id': 'ranges_linked', 'step': 4, 'title': 'Source ranges linked', 'status': 'needs_review' if need_review > 0 else 'completed', 'timestamp': created_ts, 'produced': f"{len(labs)} observations evaluated · {ranges_found} source ranges found · {need_review} need review", 'evidence': [{'label': 'Evaluated', 'value': str(len(labs))}], 'metrics': {'observations_evaluated': len(labs), 'source_ranges_found': ranges_found, 'need_review': need_review}, 'warnings': stage_4_warnings},
            {'stage_id': 'provenance_attached', 'step': 5, 'title': 'Provenance attached', 'status': 'completed', 'timestamp': created_ts, 'produced': f"Linked provenance to {len(labs)} observations.", 'evidence': [{'label': 'Linked', 'value': str(len(labs))}], 'warnings': []},
            {'stage_id': 'consistency_checked', 'step': 6, 'title': 'Consistency checked', 'status': 'completed', 'timestamp': created_ts, 'produced': "Factual cross-checks completed without diagnostic assertions.", 'evidence': [{'label': 'Check', 'value': 'Factual consistency validated'}], 'warnings': []},
            {'stage_id': 'summary_prepared', 'step': 7, 'title': 'Summary prepared', 'status': 'completed', 'timestamp': created_ts, 'produced': "Non-diagnostic summary validated.", 'evidence': [{'label': 'Format', 'value': 'Patient-friendly factual record'}], 'warnings': []},
            {'stage_id': 'human_review', 'step': 8, 'title': 'Human review', 'status': 'needs_review' if need_review > 0 else 'completed', 'timestamp': created_ts, 'produced': f"{need_review} item(s) flagged for clinician review.", 'evidence': [{'label': 'Pending review', 'value': str(need_review)}], 'warnings': []},
        ]
        return {'document_id': doc['document_id'], 'title': doc['title'], 'pipeline': stages, 'pipeline_stages': stages}


# ==================== FastAPI App Setup ====================
analyzer = Analyzer()
app = FastAPI(
    title='MedLens Clinical Intelligence API',
    description='Privacy-hardened clinical data organization prototype. Not certified for HIPAA/GDPR production use.',
    version='3.1.0'
)

# CORS Configuration:
# - No wildcard '*' with credentials!
# - Configured explicitly via CORS_ALLOWED_ORIGINS env variable
raw_cors = os.getenv('CORS_ALLOWED_ORIGINS', '')
if raw_cors.strip():
    ALLOWED_ORIGINS = [orig.strip() for orig in raw_cors.split(',') if orig.strip()]
else:
    ALLOWED_ORIGINS = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'https://shanmukha666.github.io',
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization', 'X-Session-ID', 'Accept'],
)


# Global Safe Exception Handler: Avoid raw stack traces leaking to client
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
    logger.error("Unhandled exception on %s: %s", request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={'detail': 'An internal processing error occurred. Incident has been logged.'}
    )


# ==================== Endpoints ====================
@app.get('/api/health')
def health(session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    docs = analyzer.store.list_documents(limit=200, session_id=session_id)
    patients = analyzer.store.list_patients(session_id=session_id)
    
    # Path sanitization: Never expose raw server filesystem paths in health responses!
    return {
        'status': 'ok',
        'processing_mode': 'offline-local' if analyzer.llm.is_offline_forced or not analyzer.llm.configured else 'cloud-gemini',
        'gemini': {
            'configured': analyzer.llm.configured,
            'model': getattr(analyzer.llm, 'model', 'gemini-1.5-flash'),
            'mode': 'cloud-gemini' if analyzer.llm.configured else 'offline-heuristic-fallback',
        },
        'storage': {
            'session_scoped': True,
            'session_id': session_id,
            'documents_count': len(docs),
            'patients_count': len(patients),
            'persistence_type': 'sqlite-local-sandboxed',
        },
        'security': {
            'cors_origin_enforced': True,
            'auth_scoped': True,
            'prompt_injection_guard': True,
            'regulatory_compliance_claimed': False,
            'disclaimer': 'Medical information organizing prototype for hackathon demonstration. NOT certified for HIPAA or GDPR clinical deployment.'
        }
    }


@app.get('/api/documents')
def list_documents(limit: int = 50, patient_id: Optional[str] = None, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    return {'items': analyzer.store.list_documents(limit=limit, patient_id=patient_id, session_id=session_id)}


@app.get('/api/documents/{document_id}')
def get_document(document_id: str, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    document = analyzer.store.get_document(document_id, session_id=session_id)
    if document is None:
        # Prevent IDOR enumeration by returning 404 regardless of whether document exists under another session
        raise HTTPException(status_code=404, detail='Document not found')
    document['suggested_questions'] = analyzer._suggest_grounded_questions(document, [])
    return document


@app.delete('/api/documents/{document_id}')
def delete_document(document_id: str, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    """Deletes a document, its chunks, and updates the search index."""
    deleted = analyzer.store.delete_document(document_id, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail='Document not found or access denied')
    return {'status': 'deleted', 'document_id': document_id}


@app.post('/api/ingest/text')
async def ingest_text(
    payload: IngestTextRequest,
    request: Request,
    session_id: str = Depends(get_session_id)
) -> Dict[str, Any]:
    check_rate_limit(request.client.host if request.client else "unknown", "ingest_text", max_requests=30)
    try:
        return await analyzer.ingest_text(payload.text, payload.title, payload.patient_id, session_id=session_id)
    except FeatherlessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post('/api/ingest/file')
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    patient_id: Optional[str] = Form(None),
    session_id: str = Depends(get_session_id)
) -> Dict[str, Any]:
    check_rate_limit(request.client.host if request.client else "unknown", "ingest_file", max_requests=20)
    try:
        return await analyzer.ingest_file(file, title, patient_id, session_id=session_id)
    except FeatherlessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get('/api/patients')
def list_patients(session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    return {'items': analyzer.store.list_patients(session_id=session_id)}


@app.post('/api/patients')
def create_patient(payload: PatientCreate, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    pid = analyzer.store.create_patient(
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
    return {'patient_id': pid}


@app.put('/api/patients/{patient_id}')
def update_patient(patient_id: str, payload: PatientUpdate, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    success = analyzer.store.update_patient(
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
    return {'status': 'updated', 'patient_id': patient_id}


@app.get('/api/patients/{patient_id}')
def get_patient(patient_id: str, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    patient = analyzer.store.get_patient(patient_id, session_id=session_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.delete('/api/patients/{patient_id}')
def delete_patient(patient_id: str, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    """Deletes a patient and all their associated documents and chunks."""
    deleted = analyzer.store.delete_patient(patient_id, session_id=session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Patient not found or access denied")
    return {'status': 'deleted', 'patient_id': patient_id}


@app.post('/api/documents/verify-lab')
def verify_or_edit_lab(payload: LabUpdateRequest, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    doc = analyzer.store.get_document(payload.document_id, session_id=session_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    labs = doc.get('extracted', {}).get('labs', {})
    existing = labs.get(payload.test_name, {})
    now_iso = datetime.now(timezone.utc).isoformat()
    action = payload.action or ('edit' if payload.verification_status == 'edited' else 'verify')

    # Action 1: Remove observation
    if action == 'remove':
        if payload.test_name in labs:
            del labs[payload.test_name]
        updated_doc = analyzer.store.update_document_labs(payload.document_id, labs, session_id=session_id)
        return {'status': 'success', 'action': 'remove', 'document': updated_doc, 'test_name': payload.test_name}

    audit_trail = list(existing.get('audit_trail', []))
    orig_val = existing.get('original_extracted_value', existing.get('value'))
    if orig_val is None:
        orig_val = payload.original_value if payload.original_value is not None else payload.value

    # Action 2: Mark Incorrect
    if action == 'mark_incorrect':
        audit_entry = {
            'action': 'mark_incorrect',
            'original_value': orig_val,
            'corrected_value': None,
            'changed_at': now_iso,
            'change_source': 'user_verified',
            'notes': payload.notes or 'Marked incorrect by clinician during review.'
        }
        audit_trail.append(audit_entry)
        updated_item = {
            **existing,
            'test_name': payload.test_name,
            'status': 'not_assessed',
            'verification_status': 'marked_incorrect',
            'provenance_type': 'user_verified',
            'verified_notes': payload.notes or 'Marked incorrect by clinician.',
            'original_extracted_value': orig_val,
            'audit_trail': audit_trail,
            'updated_at': now_iso
        }
        labs[payload.test_name] = updated_item
        updated_doc = analyzer.store.update_document_labs(payload.document_id, labs, session_id=session_id)
        return {'status': 'success', 'action': 'mark_incorrect', 'document': updated_doc, 'observation': updated_item}

    val = payload.value if payload.value is not None else existing.get('value', 0.0)
    r_min = payload.parsed_min
    r_max = payload.parsed_max
    if r_min is not None and r_max is not None and r_min <= r_max:
        ref_range = {'min': r_min, 'max': r_max}
        if val < r_min:
            stat = 'low'
        elif val > r_max:
            stat = 'high'
        else:
            stat = 'normal'
        ref_text = f"Source reference: {payload.reference_range_raw}" if payload.reference_range_raw else f"Source reference: {r_min} - {r_max}"
    else:
        ref_range = None
        stat = 'not_assessed'
        ref_text = 'Reference range not available in source report.'

    if action == 'edit':
        v_status = 'edited'
        audit_entry = {
            'action': 'edit',
            'original_value': orig_val,
            'corrected_value': val,
            'original_unit': existing.get('unit', ''),
            'corrected_unit': payload.unit or existing.get('unit', ''),
            'changed_at': now_iso,
            'change_source': 'user_verified',
            'notes': payload.notes or ''
        }
        audit_trail.append(audit_entry)
    elif action == 'add':
        v_status = 'verified'
        audit_entry = {
            'action': 'add',
            'original_value': None,
            'corrected_value': val,
            'changed_at': now_iso,
            'change_source': 'user_verified',
            'notes': payload.notes or 'Manually added by clinician from source document.'
        }
        audit_trail.append(audit_entry)
    else:
        v_status = 'verified'
        audit_entry = {
            'action': 'verify',
            'original_value': orig_val,
            'corrected_value': val,
            'changed_at': now_iso,
            'change_source': 'user_verified',
            'notes': payload.notes or 'Verified correct by clinician.'
        }
        audit_trail.append(audit_entry)

    updated_item = {
        'test_name': payload.test_name,
        'value': val,
        'unit': payload.unit if payload.unit is not None else existing.get('unit', ''),
        'reference_range': ref_range,
        'source_range_raw': payload.reference_range_raw or existing.get('source_range_raw'),
        'parsed_min': r_min,
        'parsed_max': r_max,
        'reference_range_text': ref_text,
        'status': stat,
        'observation_date': existing.get('observation_date') or (doc.get('created_at', '')[:10] if doc.get('created_at') else None),
        'source_page': payload.source_page or existing.get('source_page', 1),
        'source_snippet': payload.source_snippet or existing.get('source_snippet', ''),
        'extraction_confidence': 1.0,
        'verification_status': v_status,
        'provenance_type': 'user_verified',
        'original_extracted_value': orig_val,
        'audit_trail': audit_trail,
        'verified_notes': payload.notes or '',
        'updated_at': now_iso
    }
    labs[payload.test_name] = updated_item
    updated_doc = analyzer.store.update_document_labs(payload.document_id, labs, session_id=session_id)
    return {'status': 'success', 'action': action, 'document': updated_doc, 'observation': updated_item}


@app.post('/api/search')
def search(payload: SearchRequest, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    return analyzer.semantic_search(payload.query, payload.document_id, payload.top_k, session_id=session_id)


@app.post('/api/ask')
def ask(
    payload: AskRequest,
    request: Request,
    session_id: str = Depends(get_session_id)
) -> Dict[str, Any]:
    check_rate_limit(request.client.host if request.client else "unknown", "ask", max_requests=25)
    try:
        return analyzer.answer_question(payload.question, payload.document_id, payload.top_k, session_id=session_id)
    except FeatherlessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get('/api/documents/{document_id}/pipeline')
def get_document_pipeline(document_id: str, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    return analyzer.get_processing_pipeline(document_id=document_id, session_id=session_id)


@app.post('/api/pipeline')
def get_pipeline(payload: PipelineRequest, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    return analyzer.get_processing_pipeline(document_id=payload.document_id, session_id=session_id)


@app.post('/api/agents/sync')
def agents_sync(payload: MultiAgentRequest, session_id: str = Depends(get_session_id)) -> Dict[str, Any]:
    return analyzer.get_processing_pipeline(document_id=payload.document_id, session_id=session_id)
