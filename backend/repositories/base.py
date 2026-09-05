"""
Base database connection, index creation, and migration management for SQLite.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional
from backend.config import settings


class BaseRepository:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (settings.INDEX_DIR / "rag.db")
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id TEXT PRIMARY KEY,
                    session_id TEXT DEFAULT 'demo-user-session',
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
                    session_id TEXT DEFAULT 'demo-user-session',
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

                -- High-performance composite indexes
                CREATE INDEX IF NOT EXISTS idx_documents_session_created ON documents(session_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_documents_patient_session ON documents(patient_id, session_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id, chunk_index);
                CREATE INDEX IF NOT EXISTS idx_patients_session_created ON patients(session_id, created_at DESC);
                """
            )
            for col in [
                ("patients", "session_id TEXT DEFAULT 'demo-user-session'"),
                ("patients", "notes TEXT"),
                ("documents", "session_id TEXT DEFAULT 'demo-user-session'"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE {col[0]} ADD COLUMN {col[1]}")
                except Exception:
                    pass
