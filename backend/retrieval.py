from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

CHUNK_WORDS = 220
CHUNK_OVERLAP = 50
DEFAULT_SESSION_ID = "default_session"


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    document_title: str
    text: str
    score: float
    metadata: Dict[str, Any]


class RetrievalStore:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / 'rag.db'
        self.index_dir = self.base_dir / 'index'
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.vectorizer_path = self.index_dir / 'vectorizer.joblib'
        self.matrix_path = self.index_dir / 'matrix.joblib'
        self.chunk_ids_path = self.index_dir / 'chunk_ids.json'
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id TEXT PRIMARY KEY,
                    session_id TEXT DEFAULT 'default_session',
                    name TEXT NOT NULL,
                    age INTEGER,
                    sex TEXT,
                    symptoms TEXT,
                    conditions TEXT,
                    allergies TEXT,
                    medications TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    patient_id TEXT,
                    session_id TEXT DEFAULT 'default_session',
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_name TEXT,
                    raw_text TEXT NOT NULL,
                    preview_text TEXT,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    extracted_json TEXT NOT NULL,
                    ai_summary_json TEXT NOT NULL,
                    FOREIGN KEY(patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    chunk_text TEXT NOT NULL,
                    token_estimate INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(document_id) ON DELETE CASCADE
                );
                """
            )
            # Add columns if migrating an existing SQLite database
            for col in [
                ("patients", "session_id TEXT DEFAULT 'default_session'"),
                ("patients", "notes TEXT"),
                ("documents", "session_id TEXT DEFAULT 'default_session'")
            ]:
                try:
                    conn.execute(f"ALTER TABLE {col[0]} ADD COLUMN {col[1]}")
                except Exception:
                    pass

    def create_patient(
        self,
        name: str,
        age: Optional[int],
        sex: Optional[str],
        symptoms: List[str],
        conditions: List[str],
        allergies: List[str],
        medications: List[str],
        notes: Optional[str] = '',
        session_id: Optional[str] = None
    ) -> str:
        patient_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        sid = session_id or DEFAULT_SESSION_ID
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO patients (patient_id, session_id, name, age, sex, symptoms, conditions, allergies, medications, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient_id,
                    sid,
                    name,
                    age,
                    sex,
                    json.dumps(symptoms),
                    json.dumps(conditions),
                    json.dumps(allergies),
                    json.dumps(medications),
                    notes or '',
                    created_at,
                )
            )
        return patient_id

    def update_patient(
        self,
        patient_id: str,
        name: str,
        age: Optional[int],
        sex: Optional[str],
        symptoms: List[str],
        conditions: List[str],
        allergies: List[str],
        medications: List[str],
        notes: Optional[str] = '',
        session_id: Optional[str] = None
    ) -> bool:
        with self._connect() as conn:
            sql = """
                UPDATE patients
                SET name = ?, age = ?, sex = ?, symptoms = ?, conditions = ?, allergies = ?, medications = ?, notes = ?
                WHERE patient_id = ?
            """
            params = [
                name,
                age,
                sex,
                json.dumps(symptoms),
                json.dumps(conditions),
                json.dumps(allergies),
                json.dumps(medications),
                notes or '',
                patient_id,
            ]
            if session_id is not None:
                sql += ' AND session_id = ?'
                params.append(session_id)

            cursor = conn.execute(sql, params)
            return cursor.rowcount > 0

    def get_patient(self, patient_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            sql = 'SELECT * FROM patients WHERE patient_id = ?'
            params = [patient_id]
            if session_id is not None:
                sql += ' AND session_id = ?'
                params.append(session_id)

            row = conn.execute(sql, params).fetchone()
            if not row:
                return None

            doc_sql = 'SELECT document_id, title, created_at, ai_summary_json, extracted_json FROM documents WHERE patient_id = ?'
            doc_params = [patient_id]
            if session_id is not None:
                doc_sql += ' AND session_id = ?'
                doc_params.append(session_id)
            doc_sql += ' ORDER BY created_at DESC'

            docs = conn.execute(doc_sql, doc_params).fetchall()
        
        row_dict = dict(row)
        return {
            'patient_id': row_dict['patient_id'],
            'session_id': row_dict.get('session_id') or DEFAULT_SESSION_ID,
            'name': row_dict['name'],
            'age': row_dict['age'],
            'sex': row_dict['sex'],
            'symptoms': json.loads(row_dict['symptoms'] or '[]'),
            'conditions': json.loads(row_dict['conditions'] or '[]'),
            'allergies': json.loads(row_dict['allergies'] or '[]'),
            'medications': json.loads(row_dict['medications'] or '[]'),
            'notes': row_dict.get('notes') or '',
            'created_at': row_dict['created_at'],
            'documents': [
                {
                    'document_id': d['document_id'],
                    'title': d['title'],
                    'created_at': d['created_at'],
                    'ai_summary': json.loads(d['ai_summary_json']),
                    'extracted': json.loads(d['extracted_json']),
                }
                for d in docs
            ]
        }

    def list_patients(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            sql = 'SELECT patient_id, session_id, name, age, sex, created_at FROM patients'
            params = []
            if session_id is not None:
                sql += ' WHERE session_id = ?'
                params.append(session_id)
            sql += ' ORDER BY created_at DESC'
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def delete_patient(self, patient_id: str, session_id: Optional[str] = None) -> bool:
        """Deletes a patient and all their cascaded documents and chunks."""
        with self._connect() as conn:
            sql = 'SELECT patient_id FROM patients WHERE patient_id = ?'
            params = [patient_id]
            if session_id is not None:
                sql += ' AND session_id = ?'
                params.append(session_id)
            
            row = conn.execute(sql, params).fetchone()
            if not row:
                return False

            doc_rows = conn.execute('SELECT document_id FROM documents WHERE patient_id = ?', (patient_id,)).fetchall()
            for doc in doc_rows:
                conn.execute('DELETE FROM chunks WHERE document_id = ?', (doc['document_id'],))
            conn.execute('DELETE FROM documents WHERE patient_id = ?', (patient_id,))
            cursor = conn.execute('DELETE FROM patients WHERE patient_id = ?', (patient_id,))
            deleted = cursor.rowcount > 0

        if deleted:
            self.rebuild_index()
        return deleted

    def list_documents(self, limit: int = 50, patient_id: Optional[str] = None, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            conditions = []
            params: List[Any] = []
            if patient_id:
                conditions.append('patient_id = ?')
                params.append(patient_id)
            if session_id is not None:
                conditions.append('session_id = ?')
                params.append(session_id)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            sql = f"SELECT document_id, patient_id, session_id, title, source_type, source_name, created_at, preview_text, metadata_json, ai_summary_json FROM documents {where_clause} ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()

        items = []
        for row in rows:
            metadata = json.loads(row['metadata_json'])
            ai_summary = json.loads(row['ai_summary_json'])
            items.append({
                'document_id': row['document_id'],
                'patient_id': row['patient_id'],
                'session_id': row['session_id'],
                'title': row['title'],
                'source_type': row['source_type'],
                'source_name': row['source_name'],
                'created_at': row['created_at'],
                'preview_text': row['preview_text'],
                'word_count': metadata.get('words'),
                'chunk_count': metadata.get('chunk_count'),
                'review_status': 'processed',
                'tags': ai_summary.get('tags', []),
            })
        return items

    def get_document(self, document_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            sql = 'SELECT * FROM documents WHERE document_id = ?'
            params = [document_id]
            if session_id is not None:
                sql += ' AND session_id = ?'
                params.append(session_id)

            row = conn.execute(sql, params).fetchone()
            if row is None:
                return None

            chunks = conn.execute(
                'SELECT chunk_id, chunk_index, chunk_text, token_estimate, metadata_json FROM chunks WHERE document_id = ? ORDER BY chunk_index ASC',
                (document_id,),
            ).fetchall()

        return {
            'document_id': row['document_id'],
            'patient_id': row['patient_id'],
            'session_id': row['session_id'],
            'title': row['title'],
            'source_type': row['source_type'],
            'source_name': row['source_name'],
            'created_at': row['created_at'],
            'raw_text': row['raw_text'],
            'preview_text': row['preview_text'],
            'metadata': json.loads(row['metadata_json']),
            'extracted': json.loads(row['extracted_json']),
            'ai_summary': json.loads(row['ai_summary_json']),
            'chunks': [
                {
                    'chunk_id': c['chunk_id'],
                    'chunk_index': c['chunk_index'],
                    'text': c['chunk_text'],
                    'token_estimate': c['token_estimate'],
                    'metadata': json.loads(c['metadata_json']),
                }
                for c in chunks
            ],
        }

    def delete_document(self, document_id: str, session_id: Optional[str] = None) -> bool:
        """Deletes a single document, its chunks, and updates the search index."""
        with self._connect() as conn:
            sql = 'SELECT document_id, source_name FROM documents WHERE document_id = ?'
            params = [document_id]
            if session_id is not None:
                sql += ' AND session_id = ?'
                params.append(session_id)

            row = conn.execute(sql, params).fetchone()
            if not row:
                return False

            conn.execute('DELETE FROM chunks WHERE document_id = ?', (document_id,))
            cursor = conn.execute('DELETE FROM documents WHERE document_id = ?', (document_id,))
            deleted = cursor.rowcount > 0

        if deleted:
            self.rebuild_index()
        return deleted

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
        metadata = dict(metadata)
        metadata['chunk_count'] = len(chunks)
        preview_text = normalize_space(raw_text)[:1200]
        created_at = datetime.now(timezone.utc).isoformat()
        sid = session_id or DEFAULT_SESSION_ID

        with self._connect() as conn:
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
                    json.dumps(metadata),
                    json.dumps(extracted),
                    json.dumps(ai_summary),
                ),
            )
            for idx, text in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                conn.execute(
                    'INSERT INTO chunks (chunk_id, document_id, chunk_index, chunk_text, token_estimate, metadata_json) VALUES (?, ?, ?, ?, ?, ?)',
                    (
                        chunk_id,
                        document_id,
                        idx,
                        text,
                        estimate_tokens(text),
                        json.dumps({'start_word': idx * (CHUNK_WORDS - CHUNK_OVERLAP)}),
                    ),
                )
        self.rebuild_index()
        return self.get_document(document_id, session_id=sid) or {}

    def update_document_labs(self, document_id: str, labs: Dict[str, Any], session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            sql = 'SELECT extracted_json FROM documents WHERE document_id = ?'
            params = [document_id]
            if session_id is not None:
                sql += ' AND session_id = ?'
                params.append(session_id)

            row = conn.execute(sql, params).fetchone()
            if not row:
                return None
            extracted = json.loads(row['extracted_json'])
            extracted['labs'] = labs
            conn.execute(
                'UPDATE documents SET extracted_json = ? WHERE document_id = ?',
                (json.dumps(extracted), document_id)
            )
        return self.get_document(document_id, session_id=session_id)

    def rebuild_index(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT c.chunk_id, c.chunk_text, d.document_id, d.title FROM chunks c JOIN documents d ON d.document_id = c.document_id ORDER BY d.created_at ASC, c.chunk_index ASC'
            ).fetchall()
        texts = [row['chunk_text'] for row in rows]
        chunk_ids = [row['chunk_id'] for row in rows]
        if not texts:
            if self.vectorizer_path.exists():
                self.vectorizer_path.unlink(missing_ok=True)
            if self.matrix_path.exists():
                self.matrix_path.unlink(missing_ok=True)
            self.chunk_ids_path.write_text('[]', encoding='utf-8')
            return
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=12000)
        matrix = vectorizer.fit_transform(texts)
        joblib.dump(vectorizer, self.vectorizer_path)
        joblib.dump(matrix, self.matrix_path)
        self.chunk_ids_path.write_text(json.dumps(chunk_ids), encoding='utf-8')

    def search(self, query: str, limit: int = 8, document_id: Optional[str] = None, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = normalize_space(query)
        if not query:
            return []
        if not (self.vectorizer_path.exists() and self.matrix_path.exists() and self.chunk_ids_path.exists()):
            return []
        vectorizer: TfidfVectorizer = joblib.load(self.vectorizer_path)
        matrix = joblib.load(self.matrix_path)
        chunk_ids: List[str] = json.loads(self.chunk_ids_path.read_text(encoding='utf-8'))
        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, matrix).ravel()
        order = np.argsort(sims)[::-1]
        selected_chunk_ids = [chunk_ids[i] for i in order[: max(limit * 3, 20)] if sims[i] > 0]
        if not selected_chunk_ids:
            return []
        placeholders = ','.join('?' for _ in selected_chunk_ids)
        params: List[Any] = selected_chunk_ids[:]
        sql = (
            'SELECT c.chunk_id, c.chunk_text, c.metadata_json, d.document_id, d.title, d.session_id '
            'FROM chunks c JOIN documents d ON d.document_id = c.document_id '
            f'WHERE c.chunk_id IN ({placeholders})'
        )
        if document_id:
            sql += ' AND d.document_id = ?'
            params.append(document_id)
        if session_id is not None:
            sql += ' AND d.session_id = ?'
            params.append(session_id)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        by_id = {row['chunk_id']: row for row in rows}
        q_terms = {token for token in re.findall(r"[a-z0-9]+", query.lower()) if len(token) > 2}
        ranked_rows = []
        for idx in order:
            if sims[idx] <= 0:
                break
            cid = chunk_ids[idx]
            row = by_id.get(cid)
            if row is None:
                continue
            title_terms = set(re.findall(r"[a-z0-9]+", (row['title'] or '').lower()))
            title_overlap = len(q_terms & title_terms)
            boosted_score = float(sims[idx]) + (0.03 * title_overlap)
            ranked_rows.append((boosted_score, row))

        ranked_rows.sort(key=lambda item: item[0], reverse=True)
        results = []
        for boosted_score, row in ranked_rows[:limit]:
            results.append({
                'chunk_id': row['chunk_id'],
                'document_id': row['document_id'],
                'document_title': row['title'],
                'text': row['chunk_text'],
                'score': boosted_score,
                'metadata': json.loads(row['metadata_json']),
            })
        return results


def normalize_space(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text.split()) * 1.3))


def chunk_text(text: str) -> Iterable[str]:
    words = normalize_space(text).split(' ')
    if not words:
        return []
    chunks: List[str] = []
    step = CHUNK_WORDS - CHUNK_OVERLAP
    for start in range(0, len(words), step):
        chunk = ' '.join(words[start : start + CHUNK_WORDS]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks
