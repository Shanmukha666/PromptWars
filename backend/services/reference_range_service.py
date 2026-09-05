"""
Reference Range Service: Source-only reference interval extraction and evaluation.
ABSOLUTE RULE: MedLens may not contain built-in clinical normal ranges used to label patient results.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from backend.reference_range import (
    ParsedReferenceRange,
    evaluate_source_status,
    extract_labs_from_report,
    parse_source_reference_range,
)
from backend.models.domain import ObservationStatus


class ReferenceRangeService:
    @staticmethod
    def parse_interval(raw_range: Optional[str]) -> ParsedReferenceRange:
        return parse_source_reference_range(raw_range)

    @staticmethod
    def evaluate(val: Optional[float], r_min: Optional[float], r_max: Optional[float], op: Optional[str]) -> Tuple[ObservationStatus, bool]:
        """Evaluate component bounds using the canonical source-only range rules."""
        status_str, needs_rev, _ = evaluate_source_status(val, low=r_min, high=r_max, operator=op)
        return ObservationStatus(status_str), needs_rev

    @staticmethod
    def extract_from_report(text: str) -> Dict[str, Any]:
        return extract_labs_from_report(text)
