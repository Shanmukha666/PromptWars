"""
Tests for Reference-Range Safety & Zero-Hallucination Policy:
- value + source range => correct status (low, normal, high)
- missing source range => not_assessed
- NEVER falls back to built-in normal ranges
- ambiguous source range => needs_review
"""

import pytest
from backend.services.reference_range_service import ReferenceRangeService
from backend.models.domain import ObservationStatus


def test_explicit_complete_range_classification():
    # Value below source range
    stat, review = ReferenceRangeService.evaluate(val=9.0, r_min=12.0, r_max=16.0, op="between")
    assert stat == ObservationStatus.LOW
    assert review is False

    # Value within source range
    stat, review = ReferenceRangeService.evaluate(val=13.5, r_min=12.0, r_max=16.0, op="between")
    assert stat == ObservationStatus.NORMAL
    assert review is False

    # Value above source range
    stat, review = ReferenceRangeService.evaluate(val=18.2, r_min=12.0, r_max=16.0, op="between")
    assert stat == ObservationStatus.HIGH
    assert review is False


def test_missing_source_range_remains_not_assessed():
    """
    CRITICAL: Missing source reference range MUST yield 'not_assessed'.
    MedLens MUST NOT use general medical knowledge to invent or assume a range.
    """
    stat, review = ReferenceRangeService.evaluate(val=250.0, r_min=None, r_max=None, op=None)
    assert stat == ObservationStatus.NOT_ASSESSED
    assert review is True


def test_single_bound_ranges():
    # Less-than upper bound
    stat, review = ReferenceRangeService.evaluate(val=0.8, r_min=None, r_max=1.2, op="<")
    assert stat == ObservationStatus.NORMAL
    assert review is False

    stat_high, review_high = ReferenceRangeService.evaluate(val=1.5, r_min=None, r_max=1.2, op="<")
    assert stat_high == ObservationStatus.HIGH
    assert review_high is False

    # Greater-than lower bound
    stat_gt, _ = ReferenceRangeService.evaluate(val=50.0, r_min=100.0, r_max=None, op=">")
    assert stat_gt == ObservationStatus.LOW


def test_ambiguous_source_range_triggers_needs_review():
    # Inverted range (min > max)
    stat, review = ReferenceRangeService.evaluate(val=10.0, r_min=20.0, r_max=5.0, op="between")
    assert stat == ObservationStatus.NOT_ASSESSED
    assert review is True
