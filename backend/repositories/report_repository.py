"""
Report & document data access repository with chunking, in-memory search index caching,
and lazy loading of text chunks.
"""

from __future__ import annotations

import json
import math
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.repositories.base import BaseRepository
from backend.config import settings

CHUNK_WORDS = 220
CHUNK_OVERLAP = 50


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text.split()) * 1.3))


def chunk_text(text: str) -> Iterable[str]:
    words = normalize_space(text).split(" ")
    if not words:
        return []
    chunks: List[str] = []
    step = CHUNK_WORDS - CHUNK_OVERLAP
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + CHUNK_WORDS]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


class ReportRepository(BaseRepository):
    def __init__(self, db_path: Optional[Path] = None, index_dir: Optional[Path] = None):
        super().__init__(db_path)
        self.index_dir = index_dir or settings.INDEX_DIR
        self.vectorizer_path = self.index_dir / "vectorizer.joblib"
        self.matrix_path = self.index_dir / "matrix.joblib"
        self.chunk_ids_path = self.index_dir / "chunk_ids.json"

        # In-Memory Cache for fast similarity search without disk reads
        self._cache_lock = threading.Lock()
        self._cached_vectorizer: Optional[TfidfVectorizer] = None
        self._cached_matrix: Optional[Any] = None
        self._cached_chunk_ids: Optional[List[str]] = None
        self._index_dirty = True

    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conditions = []
        params: List[Any] = []
        if patient_id:
            conditions.append("patient_id = ?")
            params.append(patient_id)
        if session_id is not None:
            conditions.append("session_id = ?")
            params.append(session_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT document_id, patient_id, session_id, title, source_type, source_name, created_at, preview_text, metadata_json, ai_summary_json 
            FROM documents {where} 
            ORDER BY created_at DESC LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        items = []
        for row in rows:
            meta = json.loads(row["metadata_json"])
            summary = json.loads(row["ai_summary_json"])
            items.append({
                "document_id": row["document_id"],
                "patient_id": row["patient_id"],
                "session_id": row["session_id"],
                "title": row["title"],
                "source_type": row["source_type"],
                "source_name": row["source_name"],
                "created_at": row["created_at"],
                "preview_text": row["preview_text"],
                "word_count": meta.get("words"),
                "chunk_count": meta.get("chunk_count"),
                "review_status": "processed",
                "tags": summary.get("tags", []),
            })
        return items

    def get_document(
        self,
        document_id: str,
        session_id: Optional[str] = None,
        include_chunks: bool = True
    ) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM documents WHERE document_id = ?"
        params = [document_id]
        if session_id is not None:
            sql += " AND session_id = ?"
            params.append(session_id)

        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if row is None:
                return None

            chunks_list = []
            if include_chunks:
                chunks = conn.execute(
                    "SELECT chunk_id, chunk_index, chunk_text, token_estimate, metadata_json FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC",
                    (document_id,),
                ).fetchall()
                chunks_list = [
                    {
                        "chunk_id": c["chunk_id"],
                        "chunk_index": c["chunk_index"],
                        "text": c["chunk_text"],
                        "token_estimate": c["token_estimate"],
                        "metadata": json.loads(c["metadata_json"]),
                    }
                    for c in chunks
                ]

        return {
            "document_id": row["document_id"],
            "patient_id": row["patient_id"],
            "session_id": row["session_id"],
            "title": row["title"],
            "source_type": row["source_type"],
            "source_name": row["source_name"],
            "created_at": row["created_at"],
            "raw_text": row["raw_text"],
            "preview_text": row["preview_text"],
            "metadata": json.loads(row["metadata_json"]),
            "extracted": json.loads(row["extracted_json"]),
            "ai_summary": json.loads(row["ai_summary_json"]),
            "chunks": chunks_list,
        }

    def upsert_document(
        self,
        *,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
        title: str,
        source_type: str,
        source_name: Optional[str],
        raw_text: str,
        metadata: Dict[str, Any],
        extracted: Dict[str, Any],
        ai_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        document_id = str(uuid.uuid4())
        chunks = list(chunk_text(raw_text))
        meta = dict(metadata)
        meta["chunk_count"] = len(chunks)
        preview_text = normalize_space(raw_text)[:1200]
        created_at = datetime.now(timezone.utc).isoformat()
        sid = session_id or settings.DEFAULT_SESSION_ID

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (document_id, patient_id, session_id, title, source_type, source_name, raw_text, preview_text, created_at, metadata_json, extracted_json, ai_summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    patient_id,
                    sid,
                    title,
                    source_type,
                    source_name,
                    raw_text,
                    preview_text,
                    created_at,
                    json.dumps(meta),
                    json.dumps(extracted),
                    json.dumps(ai_summary),
                ),
            )
            for idx, text in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO chunks (chunk_id, document_id, chunk_index, chunk_text, token_estimate, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        chunk_id,
                        document_id,
                        idx,
                        text,
                        estimate_tokens(text),
                        json.dumps({"start_word": idx * (CHUNK_WORDS - CHUNK_OVERLAP)}),
                    ),
                )
        self.rebuild_index()
        return self.get_document(document_id, session_id=sid) or {}

    def update_document_labs(
        self,
        document_id: str,
        labs: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        sql = "SELECT extracted_json FROM documents WHERE document_id = ?"
        params = [document_id]
        if session_id is not None:
            sql += " AND session_id = ?"
            params.append(session_id)

        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if not row:
                return None
            extracted = json.loads(row["extracted_json"])
            extracted["labs"] = labs
            conn.execute("UPDATE documents SET extracted_json = ? WHERE document_id = ?", (json.dumps(extracted), document_id))
        return self.get_document(document_id, session_id=session_id)

    def delete_document(self, document_id: str, session_id: Optional[str] = None) -> bool:
        sql = "SELECT document_id FROM documents WHERE document_id = ?"
        params = [document_id]
        if session_id is not None:
            sql += " AND session_id = ?"
            params.append(session_id)

        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            cursor = conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
            deleted = cursor.rowcount > 0

        if deleted:
            self.rebuild_index()
        return deleted

    def rebuild_index(self) -> None:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT c.chunk_id, c.chunk_text, d.document_id, d.title FROM chunks c JOIN documents d ON d.document_id = c.document_id ORDER BY d.created_at ASC, c.chunk_index ASC"
            ).fetchall()
        texts = [r["chunk_text"] for r in rows]
        chunk_ids = [r["chunk_id"] for r in rows]
        with self._cache_lock:
            if not texts:
                if self.vectorizer_path.exists():
                    self.vectorizer_path.unlink(missing_ok=True)
                if self.matrix_path.exists():
                    self.matrix_path.unlink(missing_ok=True)
                self.chunk_ids_path.write_text("[]", encoding="utf-8")
                self._cached_vectorizer = None
                self._cached_matrix = None
                self._cached_chunk_ids = []
                self._index_dirty = False
                return

            vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=12000)
            matrix = vectorizer.fit_transform(texts)
            joblib.dump(vectorizer, self.vectorizer_path)
            joblib.dump(matrix, self.matrix_path)
            self.chunk_ids_path.write_text(json.dumps(chunk_ids), encoding="utf-8")

            # Update in-memory cache directly
            self._cached_vectorizer = vectorizer
            self._cached_matrix = matrix
            self._cached_chunk_ids = chunk_ids
            self._index_dirty = False

    def _get_in_memory_index(self) -> Tuple[Optional[TfidfVectorizer], Optional[Any], Optional[List[str]]]:
        """Returns the in-memory cached vectorizer, matrix, and chunk IDs, loading once from disk if uninitialized."""
        with self._cache_lock:
            if not self._index_dirty and self._cached_vectorizer is not None and self._cached_matrix is not None and self._cached_chunk_ids is not None:
                return self._cached_vectorizer, self._cached_matrix, self._cached_chunk_ids

            if not (self.vectorizer_path.exists() and self.matrix_path.exists() and self.chunk_ids_path.exists()):
                return None, None, None

            try:
                self._cached_vectorizer = joblib.load(self.vectorizer_path)
                self._cached_matrix = joblib.load(self.matrix_path)
                self._cached_chunk_ids = json.loads(self.chunk_ids_path.read_text(encoding="utf-8"))
                self._index_dirty = False
                return self._cached_vectorizer, self._cached_matrix, self._cached_chunk_ids
            except Exception:
                return None, None, None

    def search(
        self,
        query: str,
        limit: int = 8,
        document_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        query = normalize_space(query)
        if not query:
            return []

        vectorizer, matrix, chunk_ids = self._get_in_memory_index()
        if vectorizer is None or matrix is None or not chunk_ids:
            return []

        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, matrix).ravel()
        # Filter candidate chunk indices that have non-zero similarity
        positive_indices = [i for i, sim in enumerate(sims) if sim > 0]
        if not positive_indices:
            return []

        # Map indices to chunk_ids
        sim_map = {chunk_ids[i]: float(sims[i]) for i in positive_indices}
        placeholders = ",".join("?" for _ in sim_map.keys())
        params: List[Any] = list(sim_map.keys())

        sql = f"""
            SELECT c.chunk_id, c.chunk_text, c.metadata_json, d.document_id, d.title, d.session_id 
            FROM chunks c JOIN documents d ON d.document_id = c.document_id 
            WHERE c.chunk_id IN ({placeholders})
        """
        if document_id:
            sql += " AND d.document_id = ?"
            params.append(document_id)
        if session_id is not None:
            sql += " AND d.session_id = ?"
            params.append(session_id)

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        q_terms = {token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2}
        ranked_rows = []
        for row in rows:
            cid = row["chunk_id"]
            base_sim = sim_map.get(cid, 0.0)
            title_terms = set(re.findall(r"[a-z0-9]+", (row["title"] or "").lower()))
            title_overlap = len(q_terms & title_terms)
            boosted_score = base_sim + (0.03 * title_overlap)
            ranked_rows.append((boosted_score, row))

        ranked_rows.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, row in ranked_rows[:limit]:
            results.append({
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "document_title": row["title"],
                "text": row["chunk_text"],
                "score": score,
                "metadata": json.loads(row["metadata_json"]),
            })
        return results
