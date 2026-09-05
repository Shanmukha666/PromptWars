"""
MedLens Reference Range & Clinical Extraction Engine
Strict adherence to:
ABSOLUTE RULE:
MedLens may not contain built-in clinical normal ranges used to label patient results.

All reference intervals, upper/lower bounds, and status evaluations derive SOLELY
from the source report. Never manufactures a missing lower or upper bound.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedReferenceRange:
    raw: Optional[str]
    low: Optional[float]
    high: Optional[float]
    operator: Optional[str]  # 'between', '<', '<=', '>', '>=', 'textual'
    textual_target: Optional[str]
    is_ambiguous: bool
    needs_review: bool
    text: str


def parse_source_reference_range(raw_text: Optional[str]) -> ParsedReferenceRange:
    """
    Safely parses a source-provided reference range string.
    CRITICAL CONSTRAINTS:
    - Never manufactures a missing lower or upper bound (e.g. never assumes low=0 for '<5').
    - If the range is ambiguous, inverted, or unparseable:
      is_ambiguous = True, needs_review = True.
    """
    if not raw_text or not str(raw_text).strip():
        return ParsedReferenceRange(
            raw=None,
            low=None,
            high=None,
            operator=None,
            textual_target=None,
            is_ambiguous=False,
            needs_review=True,
            text='Reference range not available in source report.'
        )

    raw = str(raw_text).strip()
    # Normalize unicode dashes: en-dash, em-dash, minus
    normalized = raw.replace('–', '-').replace('—', '-').replace('−', '-')

    # 1. Complete numeric range: e.g. 12.0 - 16.0, [12.0-16.0], 12 to 16
    between_match = re.search(
        r'(?:(?:ref(?:\.|erence)?\s*(?:range|interval)?|normal\s*(?:range)?|expected|range)\s*[:=]?\s*)?[\[\(]?\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*[\]\)]?',
        normalized,
        re.I
    )
    if between_match and between_match.group(1) and between_match.group(2):
        try:
            low = float(between_match.group(1))
            high = float(between_match.group(2))
            if low <= high:
                return ParsedReferenceRange(
                    raw=raw,
                    low=low,
                    high=high,
                    operator='between',
                    textual_target=None,
                    is_ambiguous=False,
                    needs_review=False,
                    text=f"Source reference: {raw}"
                )
            else:
                # Inverted range (e.g. 20.0 - 10.0) -> ambiguous
                return ParsedReferenceRange(
                    raw=raw,
                    low=None,
                    high=None,
                    operator=None,
                    textual_target=None,
                    is_ambiguous=True,
                    needs_review=True,
                    text=f"Ambiguous source reference: {raw}"
                )
        except (ValueError, TypeError):
            pass

    # 2. Upper-bound-only range: e.g. <5, <= 5.0, < 5, less than 5
    upper_match = re.search(
        r'(?:(?:ref(?:\.|erence)?\s*(?:range|interval)?|normal\s*(?:range)?|expected|range)\s*[:=]?\s*)?[\[\(]?\s*(<=?|<|less\s+than)\s*(\d+(?:\.\d+)?)\s*[\]\)]?',
        normalized,
        re.I
    )
    if upper_match and upper_match.group(2):
        try:
            high = float(upper_match.group(2))
            op = '<=' if '<=' in upper_match.group(1) else '<'
            return ParsedReferenceRange(
                raw=raw,
                low=None,  # ABSOLUTE RULE: Never manufacture a missing lower bound
                high=high,
                operator=op,
                textual_target=None,
                is_ambiguous=False,
                needs_review=False,
                text=f"Source reference: {raw}"
            )
        except (ValueError, TypeError):
            pass

    # 3. Lower-bound-only range: e.g. >10, >= 10.0, greater than 10
    lower_match = re.search(
        r'(?:(?:ref(?:\.|erence)?\s*(?:range|interval)?|normal\s*(?:range)?|expected|range)\s*[:=]?\s*)?[\[\(]?\s*(>=?|>|greater\s+than)\s*(\d+(?:\.\d+)?)\s*[\]\)]?',
        normalized,
        re.I
    )
    if lower_match and lower_match.group(2):
        try:
            low = float(lower_match.group(2))
            op = '>=' if '>=' in lower_match.group(1) else '>'
            return ParsedReferenceRange(
                raw=raw,
                low=low,
                high=None,  # ABSOLUTE RULE: Never manufacture a missing upper bound
                operator=op,
                textual_target=None,
                is_ambiguous=False,
                needs_review=False,
                text=f"Source reference: {raw}"
            )
        except (ValueError, TypeError):
            pass

    # 4. Textual range: e.g. Negative, Non-reactive, Normal, Not detected
    text_match = re.search(
        r'(?:(?:ref(?:\.|erence)?\s*(?:range|interval)?|normal\s*(?:range)?|expected|range)\s*[:=]?\s*)?[\[\(]?\s*(negative|positive|non-reactive|nonreactive|reactive|normal|not\s+detected|detected|absent|present)\s*[\]\)]?',
        normalized,
        re.I
    )
    if text_match and text_match.group(1):
        target = text_match.group(1).strip().lower()
        return ParsedReferenceRange(
            raw=raw,
            low=None,
            high=None,
            operator='textual',
            textual_target=target,
            is_ambiguous=False,
            needs_review=False,
            text=f"Source reference: {raw}"
        )

    # 5. Malformed or unrecognized range -> ambiguous
    return ParsedReferenceRange(
        raw=raw,
        low=None,
        high=None,
        operator=None,
        textual_target=None,
        is_ambiguous=True,
        needs_review=True,
        text=f"Ambiguous source reference: {raw}"
    )


def evaluate_clinical_status(
    value: Any,
    parsed_range: ParsedReferenceRange,
    source_flag: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Evaluates clinical status only when comparison semantics are known.
    Returns: (status, needs_review)
    Status is strictly one of: 'low', 'normal' (within range), 'high', or 'not_assessed'
    """
    # If range is missing, malformed, or ambiguous -> not_assessed, needs_review = True
    if not parsed_range or parsed_range.raw is None or parsed_range.is_ambiguous:
        return 'not_assessed', True

    op = parsed_range.operator

    # Numeric evaluation
    try:
        val_num = float(value)
        if op == 'between':
            if parsed_range.low is not None and parsed_range.high is not None:
                if val_num < parsed_range.low:
                    return 'low', False
                elif val_num > parsed_range.high:
                    return 'high', False
                else:
                    return 'normal', False

        elif op in ('<', '<='):
            if parsed_range.high is not None:
                if op == '<':
                    if val_num < parsed_range.high:
                        return 'normal', False
                    else:
                        return 'high', False
                else:
                    if val_num <= parsed_range.high:
                        return 'normal', False
                    else:
                        return 'high', False

        elif op in ('>', '>='):
            if parsed_range.low is not None:
                if op == '>':
                    if val_num > parsed_range.low:
                        return 'normal', False
                    else:
                        return 'low', False
                else:
                    if val_num >= parsed_range.low:
                        return 'normal', False
                    else:
                        return 'low', False

    except (ValueError, TypeError):
        pass

    # Textual evaluation
    val_str = str(value).strip().lower()
    if op == 'textual' and parsed_range.textual_target:
        target = parsed_range.textual_target.lower()
        if val_str == target or (val_str in ('non-reactive', 'nonreactive') and target in ('non-reactive', 'nonreactive')):
            return 'normal', False
        if (target in ('negative', 'non-reactive', 'nonreactive', 'not detected', 'normal', 'absent') and
            val_str in ('positive', 'reactive', 'detected', 'present', 'abnormal')):
            return 'high', False
        if (target in ('positive', 'reactive', 'detected') and
            val_str in ('negative', 'non-reactive', 'nonreactive', 'not detected')):
            return 'low', False

    # Ambiguous or unknown comparison semantics
    return 'not_assessed', True


def extract_labs_from_report(text: str) -> Dict[str, Dict[str, Any]]:
    """
    Extracts laboratory observations from clinical report text.
    Preserves:
    - test_name
    - measured value (numeric or textual)
    - unit
    - source-provided reference range (raw, low, high, operator)
    - date
    - observation/flag if included in source
    - provenance & review requirements
    """
    known_tests = {
        'hemoglobin': r'(?:hemoglobin|hb)\b',
        'wbc': r'(?:wbc|white blood cell(?: count)?)\b',
        'platelets': r'(?:platelets?|plt)\b',
        'creatinine': r'(?:creatinine|creat)\b',
        'glucose': r'(?:glucose|blood sugar)\b',
        'sodium': r'(?:sodium|na)\b',
        'potassium': r'(?:potassium|k)\b',
        'calcium': r'(?:calcium|ca)\b',
        'psa': r'(?:psa|prostate specific antigen)\b',
        'inr': r'(?:inr|international normalized ratio)\b',
        'vitamin d': r'(?:vitamin\s*d|25-hydroxy vitamin d)\b',
        'hiv': r'(?:hiv(?:\s*1/2)?(?:\s*antibody)?)\b',
        'hcv': r'(?:hcv|hepatitis\s*c(?:\s*ab)?)\b',
        'hbsag': r'(?:hbsag|hepatitis\s*b\s*surface\s*antigen)\b',
        'covid-19': r'(?:covid-19|sars-cov-2)\b'
    }

    date_regex = re.compile(r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b')
    flag_regex = re.compile(r'\b(HIGH|LOW|NORMAL|ABNORMAL|CRITICAL|[HL])\b', re.I)

    # Reference range regex matching complete, upper/lower only, or textual ranges
    range_regex = re.compile(
        r'(?:(?:ref(?:\.|erence)?\s*(?:range|interval)?|normal\s*(?:range)?|expected|range)\s*[:=]?\s*)?[\[\(]?\s*(?:(?:<=?|<|>=?|>|less\s+than|greater\s+than)\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?|negative|positive|non-reactive|nonreactive|reactive|normal|not\s+detected|detected|absent|present)\s*[\]\)]?',
        re.I
    )

    out: Dict[str, Dict[str, Any]] = {}
    test_counts: Dict[str, int] = {}

    lines = text.splitlines()

    doc_dates = date_regex.findall(text)
    active_date = doc_dates[0] if doc_dates else None

    for line_idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue

        # If this line contains a date, update active_date for this and subsequent lines
        line_dates = date_regex.findall(line_clean)
        if line_dates:
            active_date = line_dates[0]

        # Scan for known tests on this line
        for test_key, test_pat in known_tests.items():
            match_test = re.search(test_pat, line_clean, re.I)
            if not match_test:
                continue

            after_test = line_clean[match_test.end():]

            # Look for value: numeric or qualitative
            val_match = re.search(
                r'[:=]?\s*([<>]?\s*\d+(?:\.\d+)?|negative|positive|non-reactive|nonreactive|reactive|normal|not\s+detected|detected)',
                after_test,
                re.I
            )
            if not val_match:
                continue

            raw_val_str = val_match.group(1).strip()
            try:
                numeric_val = float(re.sub(r'[^\d.]', '', raw_val_str))
                value = numeric_val
            except (ValueError, TypeError):
                numeric_val = None
                value = raw_val_str.capitalize()

            after_val = after_test[val_match.end():]

            # Look for unit
            unit_match = re.search(r'^\s*([a-zA-Z/%^0-9\-_]+)', after_val)
            unit = ''
            if unit_match and not re.search(r'^(ref|normal|high|low|range|negative|positive|\d)', unit_match.group(1), re.I):
                candidate_unit = unit_match.group(1)
                if len(candidate_unit) < 15 and not candidate_unit.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9', '0')):
                    unit = candidate_unit
                    after_val = after_val[unit_match.end():]

            # Look for source reference range
            range_match = range_regex.search(after_val)
            raw_range = None
            if range_match:
                raw_range = range_match.group(0).strip()
            elif line_idx + 1 < len(lines) and re.search(r'^\s*(?:reference|ref|normal)\s*(?:range)?\s*[:=]', lines[line_idx + 1], re.I):
                next_line_match = range_regex.search(lines[line_idx + 1])
                if next_line_match:
                    raw_range = next_line_match.group(0).strip()

            parsed_range = parse_source_reference_range(raw_range)

            # Look for source flag (H, L, HIGH, LOW, etc.)
            flag_match = flag_regex.search(after_val)
            source_flag = flag_match.group(1).upper() if flag_match else None

            # Evaluate status strictly against source range
            status, needs_review = evaluate_clinical_status(value, parsed_range, source_flag)

            # Unique key handling for duplicated tests
            test_counts[test_key] = test_counts.get(test_key, 0) + 1
            if test_counts[test_key] == 1:
                key = test_key
            else:
                key = f"{test_key}_{test_counts[test_key]}"

            snippet_start = max(0, match_test.start() - 20)
            snippet_end = min(len(line_clean), match_test.end() + 80)
            source_snippet = line_clean[snippet_start:snippet_end].strip()

            out[key] = {
                'test_name': test_key,
                'display_name': test_key.capitalize(),
                'value': value,
                'unit': unit,
                'reference_range_raw': parsed_range.raw,
                'reference_range_low': parsed_range.low,
                'reference_range_high': parsed_range.high,
                'reference_range_operator': parsed_range.operator,
                'reference_range': (
                    {'min': parsed_range.low, 'max': parsed_range.high}
                    if (parsed_range.low is not None and parsed_range.high is not None)
                    else None
                ),
                'parsed_min': parsed_range.low,
                'parsed_max': parsed_range.high,
                'reference_range_text': parsed_range.text,
                'status': status,
                'needs_review': needs_review,
                'source_flag': source_flag,
                'observation_date': active_date,
                'source_page': 1,
                'source_snippet': source_snippet,
                'extraction_confidence': 0.95 if (parsed_range.raw and not parsed_range.is_ambiguous) else 0.85,
                'verification_status': 'unverified',
                'provenance_type': 'source_extracted',
            }

    return out
