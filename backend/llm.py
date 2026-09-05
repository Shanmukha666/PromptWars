from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import requests

GEMINI_BASE_URL = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
GEMINI_TIMEOUT = float(os.getenv('GEMINI_TIMEOUT', '90'))


class GeminiError(RuntimeError):
    pass


# Backwards compatibility alias
FeatherlessError = GeminiError


def _strip_markdown_json(text: str) -> str:
    """Strip ```json ... ``` markdown wrappers if returned by the LLM."""
    s = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', s)
    if match:
        return match.group(1).strip()
    return s


class GeminiClient:
    """
    Google Gemini LLM client for clinical extraction, summarization, and grounded Q&A.
    Supports native Google Generative Language API (generateContent) and OpenAI-compatible proxy endpoints.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (
            api_key 
            or os.getenv('GEMINI_API_KEY', '').strip() 
            or os.getenv('GOOGLE_API_KEY', '').strip()
            or os.getenv('FEATHERLESS_API_KEY', '').strip()
        )
        self.base_url = (base_url or os.getenv('GEMINI_BASE_URL') or GEMINI_BASE_URL).rstrip('/')
        self.model = model or os.getenv('GEMINI_MODEL') or GEMINI_MODEL

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def require(self) -> None:
        if not self.configured:
            raise GeminiError('GEMINI_API_KEY is required. Add GEMINI_API_KEY=your_key to your .env file.')

    def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self.require()

        # Check if using an OpenAI-compatible proxy or native Gemini API
        if '/chat/completions' in self.base_url or '/openai' in self.base_url:
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
        """Call Google Generative Language API via native REST endpoint."""
        contents: List[Dict[str, Any]] = []
        system_instruction: Optional[Dict[str, Any]] = None

        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                system_instruction = {'parts': [{'text': content}]}
            elif role == 'assistant':
                contents.append({'role': 'model', 'parts': [{'text': content}]})
            else:
                contents.append({'role': 'user', 'parts': [{'text': content}]})

        if not contents and system_instruction:
            contents.append({'role': 'user', 'parts': [{'text': 'Begin processing based on instruction.'}]})

        generation_config: Dict[str, Any] = {
            'temperature': temperature,
            'maxOutputTokens': max_tokens,
        }
        if response_format and response_format.get('type') == 'json_object':
            generation_config['responseMimeType'] = 'application/json'

        payload: Dict[str, Any] = {
            'contents': contents,
            'generationConfig': generation_config,
        }
        if system_instruction:
            payload['systemInstruction'] = system_instruction

        model_name = self.model
        if model_name.startswith('models/'):
            model_name = model_name[7:]

        endpoint = f"{self.base_url}/models/{model_name}:generateContent?key={self.api_key}"

        try:
            response = requests.post(
                endpoint,
                headers={'Content-Type': 'application/json'},
                json=payload,
                timeout=GEMINI_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise GeminiError(f"Gemini connection error: {exc}") from exc

        if not response.ok:
            raise GeminiError(f"Gemini request failed ({response.status_code}): {response.text[:500]}")

        data = response.json()
        try:
            candidates = data.get('candidates', [])
            if not candidates:
                raise GeminiError(f"Gemini returned no candidates: {data}")
            parts = candidates[0].get('content', {}).get('parts', [])
            if not parts:
                raise GeminiError(f"Gemini candidate has no content parts: {candidates[0]}")
            raw_text = parts[0].get('text', '')
            content = _strip_markdown_json(raw_text)
        except Exception as exc:
            raise GeminiError(f"Unexpected Gemini response structure: {data}") from exc

        return {'raw': data, 'content': content}

    def _chat_openai_compatible(
        self,
        messages: List[Dict[str, Any]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1200,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Fallback for OpenAI-compatible Gemini proxy endpoints."""
        payload: Dict[str, Any] = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if response_format:
            payload['response_format'] = response_format

        endpoint = self.base_url if self.base_url.endswith('/chat/completions') else f"{self.base_url}/chat/completions"
        try:
            response = requests.post(
                endpoint,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}',
                },
                json=payload,
                timeout=GEMINI_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise GeminiError(f"Gemini proxy connection error: {exc}") from exc

        if not response.ok:
            raise GeminiError(f"Gemini proxy request failed ({response.status_code}): {response.text[:500]}")

        data = response.json()
        try:
            raw_text = data['choices'][0]['message']['content']
            content = _strip_markdown_json(raw_text)
        except Exception as exc:
            raise GeminiError(f"Unexpected Gemini proxy response: {data}") from exc

        return {'raw': data, 'content': content}

    def extract_clinical_data(self, text: str) -> Dict[str, Any]:
        prompt = (
            'You are an expert clinical data extractor for MedLens, an information intelligence assistant.\n'
            'Extract the following strictly from the provided clinical text:\n'
            '1. Lab results: test names (in lowercase), numeric values, units, and source-provided reference ranges ONLY if explicitly printed in the text (e.g., "(12.0 - 16.0)" or "Ref: 4.0 - 11.0").\n'
            '   CRITICAL CLINICAL SAFETY RULE: NEVER invent, recall, or assume reference ranges from general medical knowledge. If a reference range is not explicitly printed in the source text for that test, you MUST set "reference_range": null and "status": null.\n'
            '   Only when a reference range is explicitly present in the source text, compare value with range: mark status as "low", "high", or "normal".\n'
            '2. Entities: symptoms, conditions, medications, dates, and clinical observations explicitly mentioned in the text.\n'
            'CRITICAL SAFETY RULE: Do NOT diagnose conditions, prescribe medications, or recommend treatments.\n'
            'Return strict JSON with the exact following structure:\n'
            '{\n'
            '  "labs": {\n'
            '    "test_name_lower": {"value": 12.3, "unit": "g/dL", "reference_range": {"min": 12.0, "max": 17.5}, "status": "normal"}\n'
            '  },\n'
            '  "entities": {\n'
            '    "symptoms": ["fatigue"],\n'
            '    "conditions": ["anemia"],\n'
            '    "medications": ["iron supplement"],\n'
            '    "observations": ["pale conjunctiva"]\n'
            '  }\n'
            '}'
        )
        result = self.chat(
            [
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': text[:12000]},
            ],
            temperature=0.1,
            max_tokens=1500,
            response_format={'type': 'json_object'},
        )
        try:
            return json.loads(result['content'])
        except json.JSONDecodeError as exc:
            raise GeminiError(f'Failed to parse Gemini JSON output: {result["content"][:500]}') from exc

    def summarize_document(self, *, title: str, text: str, metadata: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            'You are an expert clinical information organizing assistant for MedLens.\n'
            'Your absolute mandate is to ORGANIZE information explicitly present in this document, NOT to diagnose or advise.\n\n'
            'SYSTEM BEHAVIOR RULES:\n'
            '- Describe ONLY what is explicitly present in the source report.\n'
            '- Highlight values outside source-provided reference ranges.\n'
            '- Mention missing or uncertain information clearly.\n'
            '- STRICTLY AVOID medical diagnosis (never state or infer diseases not explicitly affirmed in source).\n'
            '- STRICTLY AVOID causal claims unsupported by source evidence.\n'
            '- STRICTLY AVOID medication recommendations.\n'
            '- STRICTLY AVOID treatment recommendations.\n'
            '- STRICTLY AVOID dosage advice.\n'
            '- STRICTLY AVOID emergency triage claims unless directly quoting explicit source instructions.\n'
            '- Clearly identify uncertainty.\n\n'
            'Return strict JSON matching the exact following structure:\n'
            '{\n'
            '  "overview": "A concise patient-friendly paragraph describing the document type and what is explicitly present.",\n'
            '  "key_findings": ["Factual source-grounded observations directly from the report text."],\n'
            '  "outside_source_ranges": ["Only values classified using explicit source-provided ranges, e.g. HEMOGLOBIN: 9.2 g/dL (classified low against source range 12.0-16.0 g/dL). If no source range exists in the report, DO NOT include here."],\n'
            '  "medication_allergy_info": ["Factual record only of medications and allergies documented in the report, or state none documented."],\n'
            '  "items_needing_review": ["Extraction uncertainty, missing ranges, conflicts, or ambiguities requiring clinician verification."],\n'
            '  "footer": "MedLens organizes the information available in this record. It does not provide a diagnosis or treatment recommendation."\n'
            '}'
        )
        user = {
            'title': title,
            'metadata': metadata,
            'extracted': extracted,
            'text': text[:12000],
        }
        result = self.chat(
            [
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.1,
            max_tokens=1200,
            response_format={'type': 'json_object'},
        )
        try:
            return json.loads(result['content'])
        except json.JSONDecodeError as exc:
            raise GeminiError(f'Failed to parse Gemini JSON output: {result["content"][:500]}') from exc

    def answer_with_context(self, *, question: str, context_chunks: List[Dict[str, Any]], document_title: Optional[str] = None) -> Dict[str, Any]:
        context_text = '\n\n'.join(
            f"[Chunk {i+1} | score={chunk.get('score', 0):.3f} | source={chunk.get('document_title')}]\n{chunk.get('text', '')[:1500]}"
            for i, chunk in enumerate(context_chunks[:8])
        )
        system = (
            'You are a retrieval-augmented clinical intelligence assistant for MedLens. Answer questions grounded strictly in the supplied document context.\n'
            'CRITICAL SAFETY CONSTRAINTS:\n'
            '- Do NOT diagnose medical conditions, prescribe treatments, or recommend medication dosage adjustments.\n'
            '- If the user asks for diagnosis or treatment, explain factually what the document states and advise them to discuss findings with their doctor.\n'
            '- If the context is insufficient to answer the question, state that clearly rather than guessing or inferring.\n'
            '- Return strict JSON with keys: "answer", "citations", "follow_up_questions".\n'
            '- "citations" must be short grounded references indicating chunk numbers and brief relevant excerpts.\n'
            '- "follow_up_questions" must be dynamic and relevant to the document evidence.'
        )
        user = {
            'document_title': document_title,
            'question': question,
            'context': context_text,
        }
        result = self.chat(
            [
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': json.dumps(user, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={'type': 'json_object'},
        )
        try:
            return json.loads(result['content'])
        except json.JSONDecodeError as exc:
            raise GeminiError(f'Failed to parse Gemini JSON answer: {result["content"][:500]}') from exc


# Backwards compatibility alias
FeatherlessClient = GeminiClient
