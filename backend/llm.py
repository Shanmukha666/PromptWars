from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import requests

FEATHERLESS_BASE_URL = os.getenv('FEATHERLESS_BASE_URL', 'https://api.featherless.ai/v1').rstrip('/')
FEATHERLESS_MODEL = os.getenv('FEATHERLESS_MODEL', 'Qwen/Qwen2.5-7B-Instruct')
FEATHERLESS_TIMEOUT = float(os.getenv('FEATHERLESS_TIMEOUT', '90'))


class FeatherlessError(RuntimeError):
    pass


class FeatherlessClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv('FEATHERLESS_API_KEY', '').strip()
        self.base_url = (base_url or FEATHERLESS_BASE_URL).rstrip('/')
        self.model = model or FEATHERLESS_MODEL

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def require(self) -> None:
        if not self.configured:
            raise FeatherlessError('FEATHERLESS_API_KEY is required. Add it to your .env before starting the backend.')

    def chat(self, messages: List[Dict[str, Any]], *, temperature: float = 0.2, max_tokens: int = 1200, response_format: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.require()
        payload: Dict[str, Any] = {
            'model': self.model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if response_format:
            payload['response_format'] = response_format

        response = requests.post(
            f'{self.base_url}/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}',
            },
            json=payload,
            timeout=FEATHERLESS_TIMEOUT,
        )
        if not response.ok:
            raise FeatherlessError(f'Featherless request failed ({response.status_code}): {response.text[:500]}')
        data = response.json()
        try:
            content = data['choices'][0]['message']['content']
        except Exception as exc:
            raise FeatherlessError(f'Unexpected Featherless response: {data}') from exc
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
            raise FeatherlessError(f'Failed to parse Featherless JSON output: {result["content"][:500]}') from exc

    def summarize_document(self, *, title: str, text: str, metadata: Dict[str, Any], extracted: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            'You are an expert clinical information summarizer for MedLens. Create a clear, concise, patient-friendly, and clinician-reviewable factual summary of the document.\n'
            'CRITICAL CLINICAL SAFETY RULES:\n'
            '- Do NOT diagnose, prescribe, recommend treatment, recommend dosage changes, or speculate on medical outcomes.\n'
            '- Only summarize facts explicitly documented in the report.\n'
            '- Clearly indicate that this summary is informational and requires human verification.\n'
            'Return strict JSON with keys:\n'
            '  "summary": A concise patient-friendly narrative of what the report contains,\n'
            '  "bullet_points": List of key factual findings directly from the report,\n'
            '  "entities": Object containing extracted symptoms, conditions, and medications,\n'
            '  "tags": List of 3-6 relevant descriptive keywords,\n'
            '  "disclaimer": "This summary is for informational and organizational purposes only and does not constitute medical advice, diagnosis, or treatment recommendations. Always consult a licensed healthcare professional for clinical decisions."'
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
            max_tokens=900,
            response_format={'type': 'json_object'},
        )
        try:
            return json.loads(result['content'])
        except json.JSONDecodeError as exc:
            raise FeatherlessError(f'Failed to parse Featherless JSON output: {result["content"][:500]}') from exc

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
            raise FeatherlessError(f'Failed to parse Featherless JSON answer: {result["content"][:500]}') from exc
