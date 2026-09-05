from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

MANDATORY_FOOTER = "MedLens organizes the information available in this record. It does not provide a diagnosis or treatment recommendation."

FORBIDDEN_DIAGNOSTIC_PATTERNS = [
    r'\bdiagnosed with\b',
    r'\bpatient suffers from\b',
    r'\bwe prescribe\b',
    r'\brecommend taking\b',
    r'\bincrease dosage\b',
    r'\bdecrease dosage\b',
    r'\bstart treatment\b',
    r'\bemergency triage\b',
]


class ClinicalSummarySchema(BaseModel):
    """
    Strict server-side validated schema for MedLens AI clinical summarization.
    Enforces organizational information presentation rather than medical diagnosis.
    """
    overview: str = Field(
        ...,
        description="A concise patient-friendly paragraph describing what is explicitly present."
    )
    key_findings: List[str] = Field(
        default_factory=list,
        description="Factual source-grounded observations."
    )
    outside_source_ranges: List[str] = Field(
        default_factory=list,
        description="Only values classified using source-provided ranges."
    )
    medication_allergy_info: List[str] = Field(
        default_factory=list,
        description="Factual record only of medications and allergies."
    )
    items_needing_review: List[str] = Field(
        default_factory=list,
        description="Extraction uncertainty, missing ranges, conflicts, or ambiguities."
    )
    footer: str = Field(
        default=MANDATORY_FOOTER,
        description="Mandatory MedLens non-diagnostic disclaimer."
    )

    # Backwards compatibility fields for legacy UI consumption
    summary: Optional[str] = None
    bullet_points: Optional[List[str]] = None
    disclaimer: Optional[str] = None

    @field_validator('footer', mode='before')
    @classmethod
    def enforce_mandatory_footer(cls, v: Any) -> str:
        # Always enforce the exact required legal non-diagnostic disclaimer
        return MANDATORY_FOOTER

    @field_validator('overview')
    @classmethod
    def validate_overview(cls, v: str) -> str:
        text = v.strip()
        if not text:
            raise ValueError("Overview cannot be empty.")
        # Non-diagnostic safety guardrail: detect prohibited prescriptive assertions
        for pattern in FORBIDDEN_DIAGNOSTIC_PATTERNS:
            if re.search(pattern, text, re.I):
                raise ValueError(f"Overview contains ungrounded diagnostic or prescriptive phrase: {pattern}")
        return text

    @model_validator(mode='after')
    def validate_all_summary_text(self) -> 'ClinicalSummarySchema':
        for field_name in (
            'key_findings',
            'outside_source_ranges',
            'medication_allergy_info',
            'items_needing_review',
        ):
            for value in getattr(self, field_name):
                for pattern in FORBIDDEN_DIAGNOSTIC_PATTERNS:
                    if re.search(pattern, value, re.I):
                        raise ValueError(f"{field_name} contains unsafe diagnostic or prescriptive language.")
        return self

    def to_dict(self) -> Dict[str, Any]:
        data = self.model_dump()
        # Ensure backward compatibility aliases are filled
        data['summary'] = self.overview
        data['bullet_points'] = self.key_findings
        data['disclaimer'] = self.footer
        return data


def validate_or_fallback_summary(
    candidate: Any,
    title: str,
    raw_text: str,
    extracted: Dict[str, Any],
    fallback_builder: Any
) -> Dict[str, Any]:
    """
    Validates LLM output against the strict ClinicalSummarySchema.
    If the LLM output is malformed, invalid, or violates non-diagnostic rules:
    DO NOT silently treat malformed LLM output as clinical fact.
    Immediately generate a deterministic, factual structured summary and explicitly
    log the validation failure in items_needing_review.
    """
    if isinstance(candidate, dict):
        # Normalize fields if LLM returned slight variations
        norm_candidate = {
            'overview': candidate.get('overview') or candidate.get('summary') or '',
            'key_findings': candidate.get('key_findings') or candidate.get('bullet_points') or [],
            'outside_source_ranges': candidate.get('outside_source_ranges') or [],
            'medication_allergy_info': candidate.get('medication_allergy_info') or [],
            'items_needing_review': candidate.get('items_needing_review') or [],
            'footer': candidate.get('footer') or MANDATORY_FOOTER,
        }
        try:
            validated = ClinicalSummarySchema.model_validate(norm_candidate)
            return validated.to_dict()
        except Exception as exc:
            # Validation failed! Fall back to deterministic engine and flag uncertainty
            return fallback_builder(
                title=title,
                raw_text=raw_text,
                extracted=extracted,
                review_reason=f"LLM output failed schema validation ({type(exc).__name__}). Deterministic factual summary provided."
            )

    # Candidate was not even a dict
    return fallback_builder(
        title=title,
        raw_text=raw_text,
        extracted=extracted,
        review_reason="LLM response was not valid structured JSON. Deterministic factual summary provided."
    )
