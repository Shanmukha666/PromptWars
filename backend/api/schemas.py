"""
API request and response DTO schemas.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=130)
    sex: Optional[str] = Field(None, max_length=30)
    symptoms: List[str] = Field(default_factory=list, max_length=50)
    conditions: List[str] = Field(default_factory=list, max_length=50)
    allergies: List[str] = Field(default_factory=list, max_length=50)
    medications: List[str] = Field(default_factory=list, max_length=50)
    notes: Optional[str] = Field("", max_length=2000)


class PatientUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=130)
    sex: Optional[str] = Field(None, max_length=30)
    symptoms: List[str] = Field(default_factory=list, max_length=50)
    conditions: List[str] = Field(default_factory=list, max_length=50)
    allergies: List[str] = Field(default_factory=list, max_length=50)
    medications: List[str] = Field(default_factory=list, max_length=50)
    notes: Optional[str] = Field("", max_length=2000)


class LabUpdateRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=64)
    test_name: str = Field(min_length=1, max_length=100)
    action: Optional[str] = Field("verify", pattern="^(verify|edit|add|remove|mark_incorrect)$")
    value: Optional[float] = None
    unit: Optional[str] = Field("", max_length=40)
    reference_range_raw: Optional[str] = Field(None, max_length=100)
    parsed_min: Optional[float] = None
    parsed_max: Optional[float] = None
    verification_status: Optional[str] = "verified"
    notes: Optional[str] = Field(None, max_length=1000)
    original_value: Optional[float] = None
    source_page: Optional[int] = Field(1, ge=1)
    source_snippet: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_reference_bounds(self) -> "LabUpdateRequest":
        if self.parsed_min is not None and self.parsed_max is not None and self.parsed_min > self.parsed_max:
            raise ValueError("parsed_min cannot be greater than parsed_max")
        return self


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
    top_k: int = Field(4, ge=1, le=20)

# Compatibility alias
MultiAgentRequest = PipelineRequest
