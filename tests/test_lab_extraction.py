"""
Tests for Laboratory Observation Extraction:
- test name normalization
- numeric value parsing
- unit preservation
- report date extraction
- reference range parsing
"""

import pytest
from backend.services.extraction_service import ExtractionService


def test_lab_extraction_fields(extraction_service):
    report_text = """
    Date: 2026-03-15
    COMPLETE BLOOD COUNT:
    Hemoglobin: 11.2 g/dL (Ref: 12.0 - 16.0 g/dL)
    Platelets: 180 x10^3/uL (Ref: > 150)
    WBC: 7.4 10*3/uL [4.0-11.0]
    Glucose: 105 mg/dL
    """
    labs = extraction_service.extract_labs(report_text)
    
    # 1. Hemoglobin check
    assert "hemoglobin" in labs
    hb = labs["hemoglobin"]
    assert hb["value"] == 11.2
    assert hb["unit"] == "g/dL"
    assert hb["reference_range_raw"] == "Ref: 12.0 - 16.0"
    assert hb["status"] == "low"
    assert hb["needs_review"] is False

    # 2. Platelets check (lower-bound only)
    assert "platelets" in labs
    plt = labs["platelets"]
    assert plt["value"] == 180.0
    assert plt["reference_range_operator"] == ">"
    assert plt["reference_range_low"] == 150.0
    assert plt["status"] == "normal"

    # 3. WBC check (bracketed range)
    assert "wbc" in labs
    wbc = labs["wbc"]
    assert wbc["value"] == 7.4
    assert wbc["status"] == "normal"

    # 4. Glucose check (no source reference range)
    assert "glucose" in labs
    glu = labs["glucose"]
    assert glu["value"] == 105.0
    assert glu["reference_range"] is None
    assert glu["status"] == "not_assessed"


def test_entity_extraction(extraction_service):
    text = "Patient with severe fatigue, dizzy spells, and hypertension taking lisinopril and iron supplement."
    entities = extraction_service.extract_entities(text)
    assert "fatigue" in entities["symptoms"]
    assert "hypertension" in entities["conditions"]
    assert "lisinopril" in entities["medications"]
    assert "iron supplement" in entities["medications"]
