"""
Comparison & Consistency Service: Cross-checks observations against documented context without diagnosis.
"""

from __future__ import annotations
from typing import Any, Dict, List


class ComparisonService:
    @staticmethod
    def audit_reference_ranges(labs: Dict[str, Any]) -> Dict[str, Any]:
        outside = []
        within = []
        unspecified = []
        for name, item in labs.items():
            st = item.get("status")
            rec = {"test": name, "value": item.get("value"), "unit": item.get("unit"), "status": st}
            if st in {"low", "high"}:
                outside.append(rec)
            elif st == "normal":
                within.append(rec)
            else:
                unspecified.append(rec)
        return {
            "outside_source_range": outside,
            "within_source_range": within,
            "unspecified_reference_range": unspecified,
            "not_assessed": unspecified,
        }

    @staticmethod
    def corroborate_clinical_context(
        labs: Dict[str, Any],
        entities: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        obs = []
        symptoms = entities.get("symptoms", [])
        hb = labs.get("hemoglobin", {})
        if hb.get("status") == "low":
            if "fatigue" in symptoms or "dizziness" in symptoms:
                obs.append(f"Low hemoglobin ({hb.get('value')} {hb.get('unit', '')}) co-occurs with documented symptom(s).")
            else:
                obs.append("Low hemoglobin documented outside source reference range.")
        if not obs:
            obs.append("All observations consistent with documented clinical context.")
        return {
            "contextual_observations": obs,
            "safety_note": "Correlations are factual consistency checks for clinician review. MedLens does not generate diagnoses.",
        }
