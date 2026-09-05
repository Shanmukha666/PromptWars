"""
Extraction Service: Extracts labs, clinical entities, and sections from text.
"""

from __future__ import annotations
from typing import Any, Dict, List
from backend.services.reference_range_service import ReferenceRangeService


class ExtractionService:
    def __init__(self):
        self.range_service = ReferenceRangeService()

    def extract_labs(self, text: str) -> Dict[str, Any]:
        return self.range_service.extract_from_report(text)

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        t = text.lower()
        symptom_pool = [
            "fatigue", "fever", "cough", "shortness of breath", "headache",
            "dizziness", "chest pain", "nausea", "vomiting", "pain",
            "rash", "weakness", "tiredness", "pale skin"
        ]
        condition_pool = [
            "anemia", "hypertension", "diabetes", "asthma", "infection",
            "copd", "heart disease", "kidney disease", "pneumonia", "bronchitis"
        ]
        medication_pool = [
            "iron supplement", "metformin", "lisinopril", "amoxicillin",
            "ibuprofen", "aspirin", "atorvastatin", "albuterol",
            "omeprazole", "levothyroxine"
        ]
        return {
            "symptoms": [s for s in symptom_pool if s in t],
            "conditions": [c for c in condition_pool if c in t],
            "medications": [m for m in medication_pool if m in t],
        }

    def extract_sections(self, text: str) -> Dict[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections: Dict[str, str] = {}
        current_name = "General"
        current_body: List[str] = []

        for line in lines:
            if line.endswith(":") and len(line) < 40:
                if current_body:
                    sections[current_name] = " ".join(current_body)[:800]
                    current_body = []
                current_name = line[:-1]
            else:
                current_body.append(line)
        if current_body:
            sections[current_name] = " ".join(current_body)[:800]
        return sections
