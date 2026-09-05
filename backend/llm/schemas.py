"""
Pydantic validation schemas for LLM outputs.
"""

from typing import List
from pydantic import BaseModel, Field

MANDATORY_FOOTER = (
    "MedLens organizes the information available in this record. "
    "It does not provide a diagnosis or treatment recommendation."
)


class ClinicalSummarySchema(BaseModel):
    overview: str = Field(min_length=5)
    key_findings: List[str] = Field(default_factory=list)
    outside_source_ranges: List[str] = Field(default_factory=list)
    medication_allergy_info: List[str] = Field(default_factory=list)
    items_needing_review: List[str] = Field(default_factory=list)
    footer: str = Field(default=MANDATORY_FOOTER)

    @classmethod
    def enforce_footer(cls, data: dict) -> "ClinicalSummarySchema":
        data["footer"] = MANDATORY_FOOTER
        return cls.model_validate(data)
