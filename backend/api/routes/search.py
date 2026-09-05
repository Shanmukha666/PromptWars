"""
Semantic search and grounded question-answering routes.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, Request

from backend.api.dependencies import get_session_id, get_report_repo, get_llm_client, check_rate_limit
from backend.api.schemas import SearchRequest, AskRequest
from backend.repositories.report_repository import ReportRepository
from backend.llm.client import GeminiClient

logger = logging.getLogger("medlens.search")
router = APIRouter(tags=["Search"])


@router.post("/search")
def search(
    payload: SearchRequest,
    session_id: str = Depends(get_session_id),
    repo: ReportRepository = Depends(get_report_repo),
) -> Dict[str, Any]:
    results = repo.search(query=payload.query, limit=payload.top_k, document_id=payload.document_id, session_id=session_id)
    return {"query": payload.query, "count": len(results), "results": results}


@router.post("/ask")
def ask(
    payload: AskRequest,
    request: Request,
    session_id: str = Depends(get_session_id),
    repo: ReportRepository = Depends(get_report_repo),
    llm: GeminiClient = Depends(get_llm_client),
) -> Dict[str, Any]:
    check_rate_limit(request.client.host if request.client else "unknown", "ask", max_requests=25)
    chunks = repo.search(query=payload.question, limit=payload.top_k, document_id=payload.document_id, session_id=session_id)
    doc = repo.get_document(payload.document_id, session_id=session_id) if payload.document_id else None
    title = doc["title"] if doc else None

    if llm.configured:
        try:
            return llm.answer_with_context(question=payload.question, context_chunks=chunks, document_title=title)
        except Exception as e:
            logger.warning("LLM answer generation failed: %s", type(e).__name__)

    snippet = chunks[0]["text"][:300] if chunks else "No relevant document excerpt identified."
    return {
        "answer": f"Based on the clinical record: {snippet}",
        "citations": [{"chunk": 1, "text": snippet[:100]}],
        "follow_up_questions": ["What reference ranges are provided in the source report?"],
        "processing_mode": "offline-local"
    }
