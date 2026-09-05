"""
Pydantic validation schemas for LLM outputs.
"""

import re
from typing import List
from pydantic import BaseModel, Field, model_validator

MANDATORY_FOOTER = (
    "MedLens organizes the information available in this record. "
    "It does not provide a diagnosis or treatment recommendation."
)

FORBIDDEN_DIAGNOSTIC_PATTERNS = (
    r'\bdiagnosed with\b', r'\bpatient suffers from\b', r'\bwe prescribe\b',
    r'\brecommend taking\b', r'\bincrease dosage\b', r'\bdecrease dosage\b',
    r'\bstart treatment\b', r'\bemergency triage\b',
)


class ClinicalSummarySchema(BaseModel):
    overview: str = Field(min_length=5)
    key_findings: List[str] = Field(default_factory=list)
    outside_source_ranges: List[str] = Field(default_factory=list)
    medication_allergy_info: List[str] = Field(default_factory=list)
    items_needing_review: List[str] = Field(default_factory=list)
    footer: str = Field(default=MANDATORY_FOOTER)

    @model_validator(mode='after')
    def reject_unsafe_summary_language(self) -> "ClinicalSummarySchema":
        for field_name in (
            'overview', 'key_findings', 'outside_source_ranges',
            'medication_allergy_info', 'items_needing_review'
        ):
            values = getattr(self, field_name)
            for value in values if isinstance(values, list) else [values]:
                if any(re.search(pattern, value, re.I) for pattern in FORBIDDEN_DIAGNOSTIC_PATTERNS):
                    raise ValueError(f"{field_name} contains unsafe diagnostic or prescriptive language.")
        return self

    @classmethod
    def enforce_footer(cls, data: dict) -> "ClinicalSummarySchema":
        data["footer"] = MANDATORY_FOOTER
        return cls.model_validate(data)
