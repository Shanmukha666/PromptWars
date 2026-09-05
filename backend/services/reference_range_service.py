"""
Reference Range Service: Source-only reference interval extraction and evaluation.
ABSOLUTE RULE: MedLens may not contain built-in clinical normal ranges used to label patient results.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from backend.reference_range import (
    parse_source_reference_range,
    evaluate_clinical_status,
    extract_labs_from_report,
    ParsedReferenceRange,
)
from backend.models.domain import ObservationStatus, ReferenceInterval


class ReferenceRangeService:
    @staticmethod
    def parse_interval(raw_range: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        return parse_source_reference_range(raw_range)

    @staticmethod
    def evaluate(val: Optional[float], r_min: Optional[float], r_max: Optional[float], op: Optional[str]) -> Tuple[ObservationStatus, bool]:
        """Evaluate clinical status from component values by constructing a ParsedReferenceRange."""
        is_ambiguous = False
        needs_review = False
        if r_min is None and r_max is None:
            # No range at all
            raw = None
            text = "Reference range not available in source report."
            needs_review = True
        elif r_min is not None and r_max is not None and r_min > r_max:
            # Inverted range
            is_ambiguous = True
            needs_review = True
            raw = f"{r_min} - {r_max}"
            text = f"Ambiguous source reference: {raw}"
        else:
            raw = f"{r_min} - {r_max}" if r_min is not None and r_max is not None else str(r_min or r_max)
            text = f"Source reference: {raw}"

        parsed = ParsedReferenceRange(
            raw=raw,
            low=r_min,
            high=r_max,
            operator=op,
            textual_target=None,
            is_ambiguous=is_ambiguous,
            needs_review=needs_review,
            text=text,
        )
        status_str, needs_rev = evaluate_clinical_status(val, parsed)
        return ObservationStatus(status_str), needs_rev

    @staticmethod
    def extract_from_report(text: str) -> Dict[str, Any]:
        return extract_labs_from_report(text)
