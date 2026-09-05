"""
Domain models and domain-specific enums for MedLens.
Minimizes unstructured Any/Dict usage across services.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ObservationStatus(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    NOT_ASSESSED = "not_assessed"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    EDITED = "edited"
    MARKED_INCORRECT = "marked_incorrect"
    NEEDS_REVIEW = "needs_review"


class ProvenanceType(str, Enum):
    SOURCE_EXTRACTED = "source_extracted"
    USER_PROVIDED = "user_provided"
    USER_VERIFIED = "user_verified"
    AI_GENERATED = "ai_generated"


class ReferenceInterval(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    operator: Optional[str] = None  # 'between', '>', '<'
    raw_text: Optional[str] = None


class LabObservation(BaseModel):
    test_name: str
    display_name: str
    value: Optional[float] = None
    unit: str = ""
    reference_range_raw: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    reference_range_operator: Optional[str] = None
    reference_range: Optional[ReferenceInterval] = None
    source_range_raw: Optional[str] = None
    parsed_min: Optional[float] = None
    parsed_max: Optional[float] = None
    reference_range_text: str = "Reference range not available in source report."
    status: ObservationStatus = ObservationStatus.NOT_ASSESSED
    needs_review: bool = False
    source_flag: Optional[str] = None
    observation_date: Optional[str] = None
    source_page: int = 1
    source_snippet: str = ""
    extraction_confidence: float = 0.95
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    provenance_type: ProvenanceType = ProvenanceType.SOURCE_EXTRACTED
    original_extracted_value: Optional[float] = None
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)
    verified_notes: str = ""
    updated_at: Optional[str] = None


class ClinicalEntities(BaseModel):
    symptoms: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    observations: List[str] = Field(default_factory=list)


class ClinicalSummary(BaseModel):
    overview: str
    key_findings: List[str] = Field(default_factory=list)
    outside_source_ranges: List[str] = Field(default_factory=list)
    medication_allergy_info: List[str] = Field(default_factory=list)
    items_needing_review: List[str] = Field(default_factory=list)
    footer: str


class PipelineStage(BaseModel):
    stage_id: str
    step: int
    title: str
    status: str
    timestamp: str
    produced: str
    evidence: List[Dict[str, str]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class PatientProfile(BaseModel):
    patient_id: str
    session_id: str = "demo-user-session"
    name: str
    age: Optional[int] = None
    sex: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    notes: str = ""
    created_at: str
    documents: List[Dict[str, Any]] = Field(default_factory=list)


class ClinicalDocument(BaseModel):
    document_id: str
    patient_id: Optional[str] = None
    session_id: str = "demo-user-session"
    title: str
    source_type: str
    source_name: Optional[str] = None
    created_at: str
    raw_text: str
    preview_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted: Dict[str, Any] = Field(default_factory=dict)
    ai_summary: Dict[str, Any] = Field(default_factory=dict)
    chunks: List[Dict[str, Any]] = Field(default_factory=list)
