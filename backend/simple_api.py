from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.llm import GeminiClient, GeminiError, FeatherlessClient, FeatherlessError
from backend.reference_range import extract_labs_from_report, parse_source_reference_range, evaluate_clinical_status
from backend.summary_schema import ClinicalSummarySchema, validate_or_fallback_summary, MANDATORY_FOOTER
from backend.retrieval import RetrievalStore
from services.parser import get_parser_service

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'data'
UPLOAD_DIR = DATA_DIR / 'uploads'
INDEX_DIR = DATA_DIR / 'indexes'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.json', '.html', '.htm', '.docx', '.xml'}


class PatientCreate(BaseModel):
    name: str = Field(min_length=1)
    age: Optional[int] = None
    sex: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    notes: Optional[str] = ''


class PatientUpdate(BaseModel):
    name: str = Field(min_length=1)
    age: Optional[int] = None
    sex: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    notes: Optional[str] = ''


class LabUpdateRequest(BaseModel):
    document_id: str
    test_name: str
    action: Optional[str] = 'verify'  # verify, edit, mark_incorrect, remove, add
    value: Optional[float] = None
    unit: Optional[str] = ''
    reference_range_raw: Optional[str] = None
    parsed_min: Optional[float] = None
    parsed_max: Optional[float] = None
    verification_status: Optional[str] = 'verified'  # verified, edited, marked_incorrect, needs_review
    notes: Optional[str] = None
    original_value: Optional[float] = None
    source_page: Optional[int] = 1
    source_snippet: Optional[str] = None


class IngestTextRequest(BaseModel):
    text: str = Field(min_length=1)
    title: Optional[str] = None
    patient_id: Optional[str] = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: Optional[str] = None
    top_k: int = Field(default=6, ge=1, le=12)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    document_id: Optional[str] = None
    top_k: int = Field(default=8, ge=1, le=20)


class MultiAgentRequest(BaseModel):
    question: str = Field(min_length=1)
    document_id: Optional[str] = None
    top_k: int = Field(default=6, ge=1, le=12)
    simulation_overrides: Dict[str, float] = Field(default_factory=dict)


class Analyzer:
    def __init__(self) -> None:
        self.parser = get_parser_service()
        self.store = RetrievalStore(INDEX_DIR)
        self.llm = GeminiClient()

    async def ingest_file(self, upload: UploadFile, title: Optional[str] = None, patient_id: Optional[str] = None) -> Dict[str, Any]:
        if not upload.filename or not upload.filename.strip():
            raise HTTPException(status_code=400, detail='Uploaded file must have a valid filename.')
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f'Unsupported file type: "{suffix}". Allowed file types: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
            )
        
        # Enforce maximum upload size of 50MB
        MAX_UPLOAD_BYTES = 50 * 1024 * 1024
        content = await upload.read()
        if not content or len(content.strip()) == 0:
            raise HTTPException(status_code=400, detail='Uploaded file is empty (0 bytes). Please upload a valid report.')
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail='Uploaded file exceeds the maximum 50MB limit.')
            
        safe_stem = re.sub(r'[^a-zA-Z0-9_\-]', '_', Path(upload.filename or "upload").stem)[:50]
        file_path = UPLOAD_DIR / f'{safe_stem}-{uuid.uuid4().hex[:8]}{suffix}'
        file_path.write_bytes(content)
        parsed = await self.parser.parse(str(file_path))
        text = (parsed.text or '').strip()
        if not text:
            raise HTTPException(status_code=422, detail='No readable text could be extracted from the file.')
        return self._persist_document(
            patient_id=patient_id,
            title=title or upload.filename or 'Uploaded document',
            source_type=parsed.format,
            source_name=upload.filename,
            raw_text=text,
            metadata=parsed.metadata,
            tables=parsed.tables,
        )

    async def ingest_text(self, text: str, title: Optional[str] = None, patient_id: Optional[str] = None) -> Dict[str, Any]:
        clean = text.strip()
        if not clean:
            raise HTTPException(status_code=400, detail='Text input is empty.')
        return self._persist_document(
            patient_id=patient_id,
            title=title or 'Pasted text',
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
            except Exception:
                extracted = {
                    'labs': self._extract_labs(raw_text),
                    'entities': self._extract_entities(raw_text),
                }
        else:
            extracted = {
                'labs': self._extract_labs(raw_text),
                'entities': self._extract_entities(raw_text),
            }
            
        # Clinical safety audit on extracted labs:
        # Values may ONLY be marked low/normal/high if an explicit source reference range is provided!
        # ABSOLUTE RULE: MedLens may not contain built-in clinical normal ranges used to label patient results.
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
            title=title,
            source_type=source_type,
            source_name=source_name,
            raw_text=raw_text,
            metadata={**metadata, 'words': len(raw_text.split()), 'characters': len(raw_text)},
            extracted=extracted,
            ai_summary=ai_summary,
        )

    def _build_ai_summary(self, title: str, raw_text: str, metadata: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds structured clinical summary.
        Server-side validates against ClinicalSummarySchema.
        Do NOT silently treat malformed LLM output as clinical fact.
        """
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
                    review_reason=f"AI summarization service error ({type(exc).__name__}). Deterministic factual summary provided."
                )
        return self._fallback_document_summary(title=title, raw_text=raw_text, extracted=extracted)

    def answer_question(self, question: str, document_id: Optional[str], top_k: int) -> Dict[str, Any]:
        doc = self.store.get_document(document_id) if document_id else None
        grounded_query = self._prepare_grounded_query(question, doc)
        chunks = self.store.search(grounded_query, limit=top_k, document_id=document_id)
        if not chunks:
            return {
                'answer': 'I could not ground that question in the indexed PDF content yet. Try asking about a symptom, lab, diagnosis, medication, or a named section from the document.',
                'citations': [],
                'follow_up_questions': self._suggest_grounded_questions(doc, []),
                'matches': [],
                'grounded_query': grounded_query,
            }
        doc_title = doc['title'] if doc else None
        if self.llm.configured:
            try:
                answer = self.llm.answer_with_context(question=question, context_chunks=chunks, document_title=doc_title)
            except Exception:
                answer = self._fallback_answer(question=question, chunks=chunks, document=doc)
        else:
            answer = self._fallback_answer(question=question, chunks=chunks, document=doc)
        answer['matches'] = chunks
        answer['grounded_query'] = grounded_query
        if not answer.get('citations'):
            answer['citations'] = self._grounded_citations(chunks)
        answer['follow_up_questions'] = self._suggest_grounded_questions(doc, chunks)
        return answer

    def run_multi_agent(self, question: str, document_id: Optional[str], top_k: int, simulation_overrides: Dict[str, float]) -> Dict[str, Any]:
        chunks = self.store.search(question, limit=top_k, document_id=document_id)
        document = self.store.get_document(document_id) if document_id else None
        if not document and chunks:
            document = self.store.get_document(chunks[0]['document_id'])
        if document is None:
            return {
                'workflow': [],
                'final': {
                    'summary': 'No indexed evidence is available yet.',
                    'confidence': 0.0,
                    'recommended_actions': ['Ingest a document and try again.'],
                    'top_diagnoses': [],
                },
            }

        labs = json.loads(json.dumps(document.get('extracted', {}).get('labs', {})))
        for key, value in simulation_overrides.items():
            if key in labs:
                labs[key]['value'] = float(value)
                ref = labs[key].get('reference_range')
                if ref and isinstance(ref, dict) and ref.get('min') is not None and ref.get('max') is not None:
                    low = ref['min']
                    high = ref['max']
                    if value < low:
                        labs[key]['status'] = 'low'
                    elif value > high:
                        labs[key]['status'] = 'high'
                    else:
                        labs[key]['status'] = 'normal'
                else:
                    labs[key]['status'] = 'not_assessed'
                    labs[key]['reference_range_text'] = 'Reference range not available in source report.'

        entities = document.get('extracted', {}).get('entities', {})
        evidence = self._build_evidence(chunks, labs, entities, question)
        audit = self._audit_reference_ranges(labs)
        consistency = self._consistency_check(labs, entities, chunks)
        completeness = self._evaluate_data_completeness(labs, entities, document)
        final = self._compose_clinical_intelligence_summary(question, document, labs, entities, audit, consistency, completeness, evidence, simulation_overrides)

        workflow = [
            {
                'agent': 'document-processing',
                'title': 'Document Processing Agent',
                'status': 'completed',
                'summary': 'Ingested, normalized, and partitioned source document into grounded text segments.',
                'details': {
                    'document': document['title'],
                    'source_type': document['source_type'],
                    'chunk_count': len(document.get('chunks', [])),
                    'extracted_sections': [s.get('heading') for s in document.get('extracted', {}).get('sections', [])],
                },
            },
            {
                'agent': 'structured-extraction',
                'title': 'Structured Extraction Agent',
                'status': 'completed',
                'summary': 'Extracted test parameters, numeric values, units, and explicit source reference ranges.',
                'details': {
                    'extracted_parameters': {
                        name: {
                            'value': item.get('value'),
                            'unit': item.get('unit'),
                            'reference_range': item.get('reference_range_text') or 'Reference range not available in source report.',
                            'status': item.get('status') or 'not_assessed',
                        }
                        for name, item in labs.items()
                    },
                    'extracted_entities': entities,
                },
            },
            {
                'agent': 'provenance-verification',
                'title': 'Provenance Verification Agent',
                'status': 'completed',
                'summary': 'Verified laboratory values strictly against source-stated reference ranges. Flagged tests lacking ranges as "not_assessed".',
                'details': audit,
            },
            {
                'agent': 'consistency-check',
                'title': 'Consistency Check Agent',
                'status': 'completed',
                'summary': 'Cross-referenced user-provided context with report observations without diagnostic inference.',
                'details': consistency,
            },
            {
                'agent': 'summary-generation',
                'title': 'Summary Generation Agent',
                'status': 'completed',
                'summary': 'Generated a structured, reviewable clinical summary with strict non-diagnostic disclaimers.',
                'details': final,
            },
        ]
        return {
            'workflow': workflow,
            'final': final,
            'evidence': evidence,
            'simulation': {'applied_overrides': simulation_overrides, 'labs': labs},
        }

    def semantic_search(self, query: str, document_id: Optional[str], top_k: int) -> Dict[str, Any]:
        document = self.store.get_document(document_id) if document_id else None
        grounded_query = self._prepare_grounded_query(query, document)
        items = self.store.search(grounded_query, limit=top_k, document_id=document_id)
        suggestions = self._suggest_grounded_questions(document, items)
        return {
            'items': items,
            'grounded_query': grounded_query,
            'suggested_questions': suggestions,
        }

    def _prepare_grounded_query(self, question: str, document: Optional[Dict[str, Any]]) -> str:
        question = re.sub(r'\s+', ' ', (question or '').strip())
        if not document:
            return question

        entities = document.get('extracted', {}).get('entities', {}) or {}
        labs = document.get('extracted', {}).get('labs', {}) or {}
        sections = document.get('extracted', {}).get('sections', []) or []

        boosters: List[str] = []
        boosters.append(document.get('title', ''))
        for bucket in ('conditions', 'symptoms', 'medications'):
            boosters.extend(entities.get(bucket, [])[:4])
        for lab_name, payload in list(labs.items())[:5]:
            status = payload.get('status')
            if status and status != 'normal':
                boosters.append(f'{lab_name} {status}')
                boosters.append(lab_name)
        for section in sections[:3]:
            heading = (section.get('heading') or '').strip()
            if heading:
                boosters.append(heading)

        deduped: List[str] = []
        seen = set()
        for item in boosters:
            clean = re.sub(r'[^a-zA-Z0-9 /_-]+', ' ', str(item)).strip().lower()
            if len(clean) < 3 or clean in seen:
                continue
            seen.add(clean)
            deduped.append(clean)

        extra = ' '.join(deduped[:8])
        return f"{question} {extra}".strip()

    def _grounded_citations(self, chunks: List[Dict[str, Any]], limit: int = 3) -> List[str]:
        cites = []
        for idx, chunk in enumerate(chunks[:limit]):
            snippet = re.sub(r'\s+', ' ', chunk.get('text', '')).strip()[:140]
            cites.append(f"Chunk {idx + 1} · {snippet}")
        return cites

    def _suggest_grounded_questions(self, document: Optional[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> List[str]:
        suggestions: List[str] = [
            "Summarize the key findings in this report.",
            "Which values are outside the report's stated reference ranges?",
            "Which extracted fields need verification?",
            "What information changed compared with the previous report?",
        ]
        labs = (document or {}).get('extracted', {}).get('labs', {}) or {}
        sections = (document or {}).get('extracted', {}).get('sections', []) or []

        outside_labs = [name for name, payload in labs.items() if payload.get('status') in {'high', 'low'}]
        if outside_labs:
            joined = ', '.join(outside_labs[:2])
            suggestions.append(f"What are the source-stated reference ranges for {joined}?")

        not_assessed = [name for name, payload in labs.items() if payload.get('status') == 'not_assessed']
        if not_assessed:
            suggestions.append("Which extracted parameters have no reference range available in the source report?")

        for section in sections[:2]:
            heading = (section.get('heading') or '').strip()
            if heading and heading.lower() != 'extracted text':
                suggestions.append(f"What information is documented in the {heading} section?")

        out: List[str] = []
        seen = set()
        for item in suggestions:
            norm = item.lower()
            if norm in seen:
                continue
            seen.add(norm)
            out.append(item)
        return out[:6]

    def _extract_labs(self, text: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract labs strictly according to source-provided reference ranges.
        ABSOLUTE RULE: MedLens may not contain built-in clinical normal ranges used to label patient results.
        Preserves reference_range_raw, reference_range_low, reference_range_high, reference_range_operator.
        Never manufactures missing bounds. If ambiguous: status = not_assessed, needs_review = True.
        """
        return extract_labs_from_report(text)

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        lower = text.lower()
        buckets = {
            'symptoms': ['fever', 'cough', 'fatigue', 'dyspnea', 'chest pain', 'headache', 'vomiting', 'nausea', 'dizziness', 'pale skin', 'tiredness'],
            'conditions': ['diabetes', 'hypertension', 'anemia', 'sepsis', 'infection', 'kidney disease', 'asthma', 'covid', 'pneumonia'],
            'medications': ['metformin', 'insulin', 'amlodipine', 'paracetamol', 'acetaminophen', 'ibuprofen', 'aspirin', 'lisinopril'],
        }
        return {bucket: [term for term in terms if term in lower] for bucket, terms in buckets.items()}

    def _extract_sections(self, text: str) -> List[Dict[str, str]]:
        section_names = ['chief complaint', 'history', 'impression', 'assessment', 'plan', 'diagnosis', 'medications', 'recommendations']
        splitter = re.compile(r'(?i)(' + '|'.join(re.escape(name) for name in section_names) + r')\s*:')
        if not splitter.search(text):
            return [{'heading': 'Extracted text', 'content': text[:2500]}]
        pieces = splitter.split(text)
        sections: List[Dict[str, str]] = []
        for idx in range(1, len(pieces), 2):
            heading = pieces[idx].strip().title()
            content = pieces[idx + 1].strip() if idx + 1 < len(pieces) else ''
            if content:
                sections.append({'heading': heading, 'content': content[:1800]})
        return sections or [{'heading': 'Extracted text', 'content': text[:2500]}]

    def _fallback_document_summary(
        self,
        title: str,
        raw_text: str,
        extracted: Dict[str, Any],
        review_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministic factual summary organizing information strictly without diagnostic assertions.
        Conforms precisely to ClinicalSummarySchema.
        """
        labs = extracted.get('labs', {})
        entities = extracted.get('entities', {})

        # 1. Outside source ranges: ONLY values classified against explicit source-provided ranges
        outside_source_ranges = []
        for name, item in labs.items():
            st = item.get('status')
            raw_range = item.get('reference_range_raw') or item.get('source_range_raw')
            if st in {'low', 'high'} and raw_range:
                val = item.get('value')
                unit = item.get('unit', '')
                outside_source_ranges.append(
                    f"{name.upper()}: {val} {unit} (classified {st} against source reference range: {raw_range})".strip()
                )

        # 2. Key findings: factual observations directly from source
        key_findings = []
        for name, item in list(labs.items())[:6]:
            val = item.get('value')
            unit = item.get('unit', '')
            key_findings.append(f"{name.capitalize()}: {val} {unit}".strip())
        for sym in entities.get('symptoms', [])[:4]:
            key_findings.append(f"Documented symptom: {sym}")
        for cond in entities.get('conditions', [])[:3]:
            key_findings.append(f"Documented condition mention: {cond}")

        # 3. Medication & Allergy information
        medication_allergy_info = []
        meds = entities.get('medications', [])
        if meds:
            medication_allergy_info.append(f"Documented medication(s): {', '.join(meds)}")
        else:
            medication_allergy_info.append("No active medications explicitly recorded in this report.")
        allergies = entities.get('allergies', [])
        if allergies:
            medication_allergy_info.append(f"Documented allergy mention(s): {', '.join(allergies)}")

        # 4. Items needing review
        items_needing_review = []
        if review_reason:
            items_needing_review.append(review_reason)
        not_assessed = [
            f"{name.upper()} ({item.get('value')} {item.get('unit', '')}) — No reference range provided in source report (not assessed)."
            for name, item in labs.items()
            if item.get('status') == 'not_assessed'
        ]
        if not_assessed:
            items_needing_review.extend(not_assessed)
        ambiguous = [
            f"{name.upper()} — Reference range is ambiguous or malformed in source text."
            for name, item in labs.items()
            if item.get('needs_review') and item.get('status') != 'not_assessed'
        ]
        if ambiguous:
            items_needing_review.extend(ambiguous)

        # 5. Overview paragraph: concise, patient-friendly, factual, non-diagnostic
        overview = f"Factual summary of {title}. Contains {len(labs)} extracted laboratory observation(s) and {len(entities.get('symptoms', [])) + len(entities.get('conditions', []))} documented clinical context mention(s)."
        if outside_source_ranges:
            overview += f" {len(outside_source_ranges)} observation(s) fall outside source-provided reference ranges."
        if not_assessed:
            overview += f" {len(not_assessed)} observation(s) lacked source-provided reference ranges and are marked as not assessed."

        return {
            'overview': overview,
            'key_findings': key_findings or ["Document observations extracted and indexed."],
            'outside_source_ranges': outside_source_ranges,
            'medication_allergy_info': medication_allergy_info,
            'items_needing_review': items_needing_review,
            'footer': MANDATORY_FOOTER,
            # Backward compatibility aliases
            'summary': overview,
            'bullet_points': key_findings,
            'disclaimer': MANDATORY_FOOTER,
            'entities': entities,
            'tags': list(dict.fromkeys([name for name in labs.keys()]))[:6],
        }

    def _fallback_answer(self, question: str, chunks: List[Dict[str, Any]], document: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        evidence = chunks[:3]
        labs = document.get('extracted', {}).get('labs', {}) if document else {}
        entities = document.get('extracted', {}).get('entities', {}) if document else {}
        findings = []
        for name, item in labs.items():
            if item.get('status') == 'not_assessed':
                status_text = " (Reference range not available in source report.)"
            elif item.get('status'):
                status_text = f" ({item.get('status')})"
            else:
                status_text = ""
            findings.append(f"{name} {item.get('value')}{status_text}")
        if entities.get('symptoms'):
            findings.append('symptoms: ' + ', '.join(entities['symptoms']))
        summary = ' '.join(findings[:4]) or 'Relevant factual observations were found in the retrieved document chunks.'
        return {
            'answer': f"Factual report findings: {summary}. Note: MedLens provides document-grounded information only and does not diagnose or advise on treatments.",
            'citations': self._grounded_citations(evidence),
            'follow_up_questions': self._suggest_grounded_questions(document, evidence),
        }

    def _build_evidence(self, chunks: List[Dict[str, Any]], labs: Dict[str, Any], entities: Dict[str, Any], question: str) -> List[Dict[str, Any]]:
        cards: List[Dict[str, Any]] = []
        for name, item in labs.items():
            status = item.get('status') or 'not_assessed'
            ref_text = item.get('reference_range_text') or ('Reference range not available in source report.' if status == 'not_assessed' else 'Source range documented')
            cards.append({
                'type': 'lab',
                'label': name,
                'value': f"{item.get('value')} {item.get('unit', '')}".strip(),
                'status': status,
                'reason': ref_text,
            })
        for symptom in entities.get('symptoms', [])[:4]:
            cards.append({'type': 'symptom', 'label': symptom, 'value': 'documented', 'status': 'supporting', 'reason': 'Documented patient symptom in source'})
        for cond in entities.get('conditions', [])[:3]:
            cards.append({'type': 'condition', 'label': cond, 'value': 'documented', 'status': 'supporting', 'reason': 'Documented medical condition in source'})
        for idx, chunk in enumerate(chunks[:3]):
            cards.append({'type': 'chunk', 'label': f'Source chunk {idx + 1}', 'value': round(float(chunk.get('score', 0.0)), 3), 'status': 'retrieved', 'reason': chunk.get('text', '')[:160]})
        return cards

    def _audit_reference_ranges(self, labs: Dict[str, Any]) -> Dict[str, Any]:
        outside_range = []
        within_range = []
        not_assessed = []
        for name, item in labs.items():
            val = item.get('value')
            unit = item.get('unit', '')
            status = item.get('status')
            ref = item.get('reference_range')
            ref_text = item.get('reference_range_text') or ('Reference range not available in source report.' if not ref else f"Source reference: {ref.get('min')}–{ref.get('max')} {unit}".strip())

            raw_range = item.get('reference_range_raw') or item.get('source_range_raw')
            if status == 'not_assessed' or (not ref and not raw_range):
                not_assessed.append({
                    'test': name,
                    'value': f"{val} {unit}".strip(),
                    'source_range': None,
                    'status': 'not_assessed',
                    'reference_range_text': 'Reference range not available in source report.',
                    'provenance': 'Reference range not available in source report. Clinical ranges are never invented.',
                })
            else:
                r_min, r_max = ref['min'], ref['max']
                record = {
                    'test': name,
                    'value': f"{val} {unit}".strip(),
                    'source_range': f"{r_min}–{r_max} {unit}".strip(),
                    'status': status,
                    'reference_range_text': ref_text,
                    'provenance': 'Evaluated strictly against source-provided reference range',
                }
                if status in {'low', 'high'}:
                    outside_range.append(record)
                else:
                    within_range.append(record)

        return {
            'outside_source_range': outside_range,
            'within_source_range': within_range,
            'not_assessed': not_assessed,
            'unspecified_reference_range': not_assessed,
            'safety_verification': 'Values receive status "low", "normal", or "high" ONLY when explicit reference ranges exist in the source report. Ranges are never invented.',
        }

    def _consistency_check(self, labs: Dict[str, Any], entities: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        correlations = []
        symptoms = set(entities.get('symptoms', []))
        conditions = set(entities.get('conditions', []))

        hb = labs.get('hemoglobin', {})
        if hb.get('status') == 'low':
            related = {'fatigue', 'tiredness', 'dizziness', 'pale skin', 'dyspnea'} & symptoms
            if related:
                correlations.append(f"Low hemoglobin ({hb.get('value')} {hb.get('unit', '')}) co-occurs with documented symptom(s): {', '.join(related)}.")
            else:
                correlations.append(f"Low hemoglobin ({hb.get('value')} {hb.get('unit', '')}) documented outside source reference range.")

        wbc = labs.get('wbc', {})
        if wbc.get('status') == 'high':
            related = {'fever', 'cough'} & symptoms
            if related:
                correlations.append(f"Elevated WBC ({wbc.get('value')} {wbc.get('unit', '')}) co-occurs with documented symptom(s): {', '.join(related)}.")

        plt = labs.get('platelets', {})
        if plt.get('status') == 'low':
            correlations.append(f"Platelet count ({plt.get('value')} {plt.get('unit', '')}) documented below source reference range.")

        not_assessed_count = sum(1 for item in labs.values() if item.get('status') == 'not_assessed')
        if not_assessed_count > 0:
            correlations.append(f"{not_assessed_count} parameter(s) lack source-stated reference ranges and are marked 'not_assessed'.")

        if not correlations:
            correlations.append("Extracted test parameters show no out-of-range flags based on available source reference ranges.")

        return {
            'contextual_observations': correlations,
            'documented_symptoms': list(symptoms),
            'documented_conditions': list(conditions),
            'safety_note': 'Correlations are factual consistency checks for clinician review. MedLens does not generate diagnoses.',
        }

    def _corroborate_clinical_context(self, labs: Dict[str, Any], entities: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._consistency_check(labs, entities, chunks)

    def _evaluate_data_completeness(self, labs: Dict[str, Any], entities: Dict[str, Any], document: Dict[str, Any]) -> Dict[str, Any]:
        notes = []
        no_ref = [name for name, item in labs.items() if item.get('status') == 'not_assessed']
        if no_ref:
            notes.append(f"Source report did not specify explicit reference ranges for: {', '.join(no_ref)} (marked 'not_assessed').")
        if not entities.get('medications'):
            notes.append("No active medications recorded in this report.")
        if not entities.get('allergies'):
            notes.append("No allergy information recorded in this report.")
        return {
            'completeness_notes': notes or ['All extracted lab tests have explicit source-provided reference ranges.'],
            'provenance_verified': True,
            'source_document': document.get('title', 'Unknown'),
        }

    def _compose_clinical_intelligence_summary(
        self,
        question: str,
        document: Dict[str, Any],
        labs: Dict[str, Any],
        entities: Dict[str, Any],
        audit: Dict[str, Any],
        consistency: Dict[str, Any],
        completeness: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        simulation_overrides: Dict[str, float]
    ) -> Dict[str, Any]:
        outside = audit.get('outside_source_range', [])
        within = audit.get('within_source_range', [])
        not_assessed = audit.get('not_assessed', [])

        if outside:
            flagged_text = f"{len(outside)} parameter(s) outside source reference ranges: " + "; ".join(
                f"{item['test']} ({item['value']}, {item.get('reference_range_text')})" for item in outside
            )
        else:
            flagged_text = "All evaluated parameters with source reference ranges are within expected limits."

        if not_assessed:
            flagged_text += f" ({len(not_assessed)} parameter(s) marked 'not_assessed' - Reference range not available in source report.)"

        summary = f"Structured Intelligence Report for {document['title']}. {flagged_text}"
        if simulation_overrides:
            summary += f" [SIMULATION ACTIVE: values adjusted for {', '.join(simulation_overrides.keys())}. Results reflect manual overrides, not source report.]"

        return {
            'summary': summary,
            'outside_source_range': outside,
            'within_source_range': within,
            'not_assessed': not_assessed,
            'clinical_context': consistency.get('contextual_observations', []),
            'completeness_notes': completeness.get('completeness_notes', []),
            'document_title': document['title'],
            'question': question,
            'disclaimer': 'MedLens is an AI clinical information tool. It does NOT diagnose conditions, prescribe treatments, or recommend dosage changes. Review all records with a qualified healthcare provider.',
            'evidence_count': len(evidence),
        }


analyzer = Analyzer()
app = FastAPI(title='MedLens Clinical Intelligence API', version='3.0.0')

# Restrict CORS to known origins instead of wildcard '*'
ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/api/health')
def health() -> Dict[str, Any]:
    docs = analyzer.store.list_documents(limit=200)
    return {
        'status': 'ok',
        'gemini': {
            'configured': analyzer.llm.configured,
            'model': getattr(analyzer.llm, 'model', 'gemini-1.5-flash'),
            'base_url': getattr(analyzer.llm, 'base_url', 'https://generativelanguage.googleapis.com/v1beta'),
            'mode': 'live-gemini-llm' if analyzer.llm.configured else 'offline-heuristic-fallback',
        },
        'featherless': {
            'configured': analyzer.llm.configured,
            'model': getattr(analyzer.llm, 'model', 'gemini-1.5-flash'),
            'mode': 'live-gemini-llm' if analyzer.llm.configured else 'offline-heuristic-fallback',
        },
        'storage': {'documents': len(docs), 'upload_dir': str(UPLOAD_DIR), 'index_dir': str(INDEX_DIR)},
        'features': [
            'pdf-text-ingestion',
            'semantic-search',
            'grounded-qa',
            'multi-agent-sync',
            'simulation-mode',
            'api-demo-panel',
        ],
    }


@app.get('/api/documents')
def list_documents(limit: int = 50) -> Dict[str, Any]:
    return {'items': analyzer.store.list_documents(limit=limit)}


@app.get('/api/documents/{document_id}')
def get_document(document_id: str) -> Dict[str, Any]:
    document = analyzer.store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail='Document not found')
    document['suggested_questions'] = analyzer._suggest_grounded_questions(document, [])
    return document


@app.post('/api/ingest/text')
async def ingest_text(payload: IngestTextRequest) -> Dict[str, Any]:
    try:
        return await analyzer.ingest_text(payload.text, payload.title, payload.patient_id)
    except FeatherlessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post('/api/ingest/file')
async def ingest_file(file: UploadFile = File(...), title: Optional[str] = Form(None), patient_id: Optional[str] = Form(None)) -> Dict[str, Any]:
    try:
        return await analyzer.ingest_file(file, title, patient_id)
    except FeatherlessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get('/api/patients')
def list_patients() -> Dict[str, Any]:
    return {'items': analyzer.store.list_patients()}


@app.post('/api/patients')
def create_patient(payload: PatientCreate) -> Dict[str, Any]:
    pid = analyzer.store.create_patient(
        name=payload.name,
        age=payload.age,
        sex=payload.sex,
        symptoms=payload.symptoms,
        conditions=payload.conditions,
        allergies=payload.allergies,
        medications=payload.medications,
        notes=payload.notes,
    )
    return {'patient_id': pid}


@app.put('/api/patients/{patient_id}')
def update_patient(patient_id: str, payload: PatientUpdate) -> Dict[str, Any]:
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
    )
    if not success:
        raise HTTPException(status_code=404, detail="Patient not found or could not be updated")
    return {'status': 'updated', 'patient_id': patient_id}


@app.get('/api/patients/{patient_id}')
def get_patient(patient_id: str) -> Dict[str, Any]:
    patient = analyzer.store.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.post('/api/documents/verify-lab')
def verify_or_edit_lab(payload: LabUpdateRequest) -> Dict[str, Any]:
    doc = analyzer.store.get_document(payload.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    labs = doc.get('extracted', {}).get('labs', {})
    existing = labs.get(payload.test_name, {})
    now_iso = datetime.utcnow().isoformat() + "Z"
    
    action = payload.action or ('edit' if payload.verification_status == 'edited' else 'verify')

    # Action 1: Remove observation
    if action == 'remove':
        if payload.test_name in labs:
            del labs[payload.test_name]
        updated_doc = analyzer.store.update_document_labs(payload.document_id, labs)
        return {'status': 'success', 'action': 'remove', 'document': updated_doc, 'test_name': payload.test_name}

    # Extract existing audit trail & original value
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
        updated_doc = analyzer.store.update_document_labs(payload.document_id, labs)
        return {'status': 'success', 'action': 'mark_incorrect', 'document': updated_doc, 'observation': updated_item}

    # Values for verify, edit, add
    val = payload.value if payload.value is not None else existing.get('value', 0.0)
    r_min = payload.parsed_min
    r_max = payload.parsed_max
    if r_min is not None and r_max is not None and r_min <= r_max:
        ref_range = {'min': r_min, 'max': r_max}
        if val < r_min:
            status = 'low'
        elif val > r_max:
            status = 'high'
        else:
            status = 'normal'
        ref_text = f"Source reference: {payload.reference_range_raw}" if payload.reference_range_raw else f"Source reference: {r_min} - {r_max}"
    else:
        ref_range = None
        status = 'not_assessed'
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
    else:  # verify
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
        'status': status,
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
    updated_doc = analyzer.store.update_document_labs(payload.document_id, labs)
    return {'status': 'success', 'action': action, 'document': updated_doc, 'observation': updated_item}


@app.post('/api/search')
def search(payload: SearchRequest) -> Dict[str, Any]:
    return analyzer.semantic_search(payload.query, payload.document_id, payload.top_k)


@app.post('/api/ask')
def ask(payload: AskRequest) -> Dict[str, Any]:
    try:
        return analyzer.answer_question(payload.question, payload.document_id, payload.top_k)
    except FeatherlessError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post('/api/agents/sync')
def agents_sync(payload: MultiAgentRequest) -> Dict[str, Any]:
    return analyzer.run_multi_agent(payload.question, payload.document_id, payload.top_k, payload.simulation_overrides)
