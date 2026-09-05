"""
Prompt injection defense and payload sanitization utilities.
"""

def sanitize_for_evidence(text: str, max_chars: int = 10000) -> str:
    """
    Sanitize and truncate document evidence to minimize payload
    and prevent prompt injection escaping.
    """
    cleaned = (text or "").strip()[:max_chars]
    cleaned = cleaned.replace("</untrusted_clinical_evidence>", "[untrusted_clinical_evidence_closed]")
    return cleaned
