"""
MedLens LLM Client & Prompt Subsystem.
"""
from backend.llm.client import GeminiClient
from backend.llm.safety import sanitize_for_evidence
from backend.exceptions import LLMServiceError as GeminiError

# Compatibility alias
FeatherlessClient = GeminiClient
FeatherlessError = GeminiError
