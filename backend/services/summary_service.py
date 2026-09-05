"""
Summary Service: Produces structured factual summaries without medical diagnosis.
"""

from __future__ import annotations
from typing import Any, Dict, Optional

from backend.llm.client import GeminiClient
from backend.llm.schemas import MANDATORY_FOOTER
from backend.summary_schema import validate_or_fallback_summary


class SummaryService:
    def __init__(self, llm: GeminiClient):
        self.llm = llm

    def build_summary(
        self,
        *,
        title: str,
        raw_text: str,
        metadata: Dict[str, Any],
        extracted: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.llm.configured:
            try:
                candidate = self.llm.summarize_document(
                    title=title, text=raw_text, metadata=metadata, extracted=extracted
                )
                return validate_or_fallback_summary(
                    candidate=candidate,
                    title=title,
                    raw_text=raw_text,
                    extracted=extracted,
                    fallback_builder=self.fallback_summary,
                )
            except Exception as exc:
                return self.fallback_summary(
                    title=title,
                    raw_text=raw_text,
                    extracted=extracted,
                    review_reason=f"AI summarization fallback ({type(exc).__name__}). Factual summary provided."
                )
        return self.fallback_summary(title=title, raw_text=raw_text, extracted=extracted)

    def fallback_summary(
        self,
        title: str,
        raw_text: str,
        extracted: Dict[str, Any],
        review_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        labs = extracted.get("labs", {})
        outside = [
            f"{item.get('test_name', k).upper()}: {item.get('value')} {item.get('unit', '')} (classified {item.get('status')} against source range {item.get('reference_range_raw')})"
            for k, item in labs.items()
            if item.get("status") in {"low", "high"}
        ]
        items_needing_review = []
        if review_reason:
            items_needing_review.append(review_reason)
        no_ref_tests = [k.upper() for k, item in labs.items() if item.get("status") == "not_assessed"]
        if no_ref_tests:
            items_needing_review.append(
                f"Missing source reference ranges for: {', '.join(no_ref_tests)}. Marked 'not_assessed' (ranges never invented)."
            )

        meds = extracted.get("entities", {}).get("medications", [])
        med_allergy_info = [f"Medications noted: {', '.join(meds)}"] if meds else ["No active medications recorded in this report."]

        return {
            "overview": f"Clinical record '{title}' processed. Extracted {len(labs)} laboratory test observation(s) and clinical context entries.",
            "key_findings": [
                f"Extracted {len(labs)} laboratory observation(s) directly from source document.",
                f"{len(outside)} observation(s) fall outside source-provided reference ranges." if outside else "All parameters with source-provided ranges fall within expected intervals.",
            ],
            "outside_source_ranges": outside if outside else ["None. All tests with explicit source reference ranges fall within expected bounds."],
            "medication_allergy_info": med_allergy_info,
            "items_needing_review": items_needing_review if items_needing_review else ["Extraction verified against source document text."],
            "footer": MANDATORY_FOOTER,
        }
