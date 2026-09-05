"""
Google Gemini client with native REST API and OpenAI-compatible proxy support.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
import requests

from backend.config import settings
from backend.exceptions import LLMServiceError
from backend.llm.safety import sanitize_for_evidence
from backend.llm.prompts import EXTRACTION_SYSTEM_PROMPT, SUMMARY_SYSTEM_PROMPT, QA_SYSTEM_PROMPT
from backend.llm.schemas import ClinicalSummarySchema


def _strip_markdown_json(text: str) -> str:
    s = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if match:
        return match.group(1).strip()
    return s


class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = (base_url or settings.GEMINI_BASE_URL).rstrip("/")
        self.model = model or settings.GEMINI_MODEL

    @property
    def is_offline_forced(self) -> bool:
        return settings.is_offline_forced

    @property
    def configured(self) -> bool:
        if self.is_offline_forced:
            return False
        return bool(self.api_key)

    def require(self) -> None:
        if self.is_offline_forced:
            raise LLMServiceError("MedLens is configured in OFFLINE / LOCAL-ONLY mode. External LLM calls are disabled.")
        if not self.configured:
            raise LLMServiceError("GEMINI_API_KEY is required. Add GEMINI_API_KEY=your_key to your .env file or enable local processing mode.")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self.require()

        if "/chat/completions" in self.base_url or "/openai" in self.base_url:
            return self._chat_openai_compatible(messages, temperature=temperature, max_tokens=max_tokens, response_format=response_format)
        return self._chat_gemini_native(messages, temperature=temperature, max_tokens=max_tokens, response_format=response_format)

    def _chat_gemini_native(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        contents: List[Dict[str, Any]] = []
        system_instruction: Optional[Dict[str, Any]] = None

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
            else:
                contents.append({"role": "user", "parts": [{"text": content}]})

        if not contents and system_instruction:
            contents.append({"role": "user", "parts": [{"text": "Begin processing based on instruction."}]})

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if response_format and response_format.get("type") == "json_object":
            generation_config["responseMimeType"] = "application/json"

        payload = {
            "contents": contents,
            "generationConfig": generation_config,
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        model_name = self.model
        if model_name.startswith("models/"):
            model_name = model_name[7:]

        endpoint = f"{self.base_url}/models/{model_name}:generateContent"

        try:
            response = requests.post(
                endpoint,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                json=payload,
                timeout=settings.GEMINI_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise LLMServiceError(f"Gemini connection error: {exc}") from exc

        if not response.ok:
            safe_text = response.text.replace(self.api_key, "[REDACTED_API_KEY]") if self.api_key else response.text
            raise LLMServiceError(f"Gemini request failed ({response.status_code}): {safe_text[:300]}")

        data = response.json()
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMServiceError("Gemini returned no candidates.")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise LLMServiceError("Gemini candidate has no content parts.")
            raw_text = parts[0].get("text", "")
            content = _strip_markdown_json(raw_text)
        except Exception as exc:
            raise LLMServiceError(f"Unexpected Gemini response: {exc}") from exc

        return {"raw": data, "content": content}

    def _chat_openai_compatible(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        endpoint = self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=payload,
                timeout=settings.GEMINI_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise LLMServiceError(f"Gemini proxy connection error: {exc}") from exc

        if not response.ok:
            safe_text = response.text.replace(self.api_key, "[REDACTED_API_KEY]") if self.api_key else response.text
            raise LLMServiceError(f"Gemini proxy request failed ({response.status_code}): {safe_text[:300]}")

        data = response.json()
        try:
            raw_text = data["choices"][0]["message"]["content"]
            content = _strip_markdown_json(raw_text)
        except Exception as exc:
            raise LLMServiceError("Unexpected Gemini proxy response.") from exc

        return {"raw": data, "content": content}

    def extract_clinical_data(self, text: str) -> Dict[str, Any]:
        safe_text = sanitize_for_evidence(text, max_chars=10000)
        user_content = f"<untrusted_clinical_evidence>\n{safe_text}\n</untrusted_clinical_evidence>"
        result = self.chat(
            [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError as exc:
            raise LLMServiceError(f'Failed to parse Gemini JSON output: {result["content"][:300]}') from exc

    def summarize_document(self, *, title: str, text: str, metadata: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
        safe_text = sanitize_for_evidence(text, max_chars=8000)
        minimal_extracted = {
            "lab_count": len(extracted.get("labs", {})),
            "labs_outside_range": [
                {"test": k, "value": v.get("value"), "range": v.get("reference_range_raw")}
                for k, v in extracted.get("labs", {}).items()
                if v.get("status") in {"low", "high"}
            ],
            "documented_symptoms": extracted.get("entities", {}).get("symptoms", [])[:10],
            "documented_conditions": extracted.get("entities", {}).get("conditions", [])[:10],
            "documented_medications": extracted.get("entities", {}).get("medications", [])[:10],
        }
        user = {
            "title": title[:100],
            "extracted_summary": minimal_extracted,
            "evidence": f"<untrusted_clinical_evidence>\n{safe_text}\n</untrusted_clinical_evidence>",
        }
        result = self.chat(
            [
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError as exc:
            raise LLMServiceError(f'Failed to parse Gemini JSON output: {result["content"][:300]}') from exc

    def answer_with_context(self, *, question: str, context_chunks: List[Dict[str, Any]], document_title: Optional[str] = None) -> Dict[str, Any]:
        context_text = "\n\n".join(
            f"[Evidence Chunk {i+1} | Document: {chunk.get('document_title', 'Unknown')[:80]}]\n"
            f"<untrusted_clinical_evidence>\n{sanitize_for_evidence(chunk.get('text', ''), max_chars=1200)}\n</untrusted_clinical_evidence>"
            for i, chunk in enumerate(context_chunks[:6])
        )
        user = {
            "document_title": (document_title or "Clinical Report")[:100],
            "question": question[:500],
            "context_evidence": context_text,
        }
        result = self.chat(
            [
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(result["content"])
        except json.JSONDecodeError as exc:
            raise LLMServiceError(f'Failed to parse Gemini JSON answer: {result["content"][:300]}') from exc
