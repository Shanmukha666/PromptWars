"""
Patient data access repository with strict session scoping.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.repositories.base import BaseRepository
from backend.config import settings


class PatientRepository(BaseRepository):
    def create_patient(
        self,
        *,
        name: str,
        age: Optional[int],
        sex: Optional[str],
        symptoms: List[str],
        conditions: List[str],
        allergies: List[str],
        medications: List[str],
        notes: Optional[str] = "",
        session_id: Optional[str] = None
    ) -> str:
        patient_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        sid = session_id or settings.DEFAULT_SESSION_ID

        with self.connect() as conn:
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
                    notes or "",
                    created_at,
                )
            )
        return patient_id

    def update_patient(
        self,
        *,
        patient_id: str,
        name: str,
        age: Optional[int],
        sex: Optional[str],
        symptoms: List[str],
        conditions: List[str],
        allergies: List[str],
        medications: List[str],
        notes: Optional[str] = "",
        session_id: Optional[str] = None
    ) -> bool:
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
            notes or "",
            patient_id,
        ]
        if session_id is not None:
            sql += " AND session_id = ?"
            params.append(session_id)

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount > 0

    def get_patient(self, patient_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM patients WHERE patient_id = ?"
        params = [patient_id]
        if session_id is not None:
            sql += " AND session_id = ?"
            params.append(session_id)

        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if not row:
                return None

            doc_sql = "SELECT document_id, title, created_at, ai_summary_json, extracted_json FROM documents WHERE patient_id = ?"
            doc_params = [patient_id]
            if session_id is not None:
                doc_sql += " AND session_id = ?"
                doc_params.append(session_id)
            doc_sql += " ORDER BY created_at DESC"

            docs = conn.execute(doc_sql, doc_params).fetchall()

        r = dict(row)
        return {
            "patient_id": r["patient_id"],
            "session_id": r.get("session_id", settings.DEFAULT_SESSION_ID),
            "name": r["name"],
            "age": r["age"],
            "sex": r["sex"],
            "symptoms": json.loads(r["symptoms"] or "[]"),
            "conditions": json.loads(r["conditions"] or "[]"),
            "allergies": json.loads(r["allergies"] or "[]"),
            "medications": json.loads(r["medications"] or "[]"),
            "notes": r.get("notes") or "",
            "created_at": r["created_at"],
            "documents": [
                {
                    "document_id": d["document_id"],
                    "title": d["title"],
                    "created_at": d["created_at"],
                    "ai_summary": json.loads(d["ai_summary_json"]),
                    "extracted": json.loads(d["extracted_json"]),
                }
                for d in docs
            ],
        }

    def list_patients(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT patient_id, session_id, name, age, sex, created_at FROM patients"
        params = []
        if session_id is not None:
            sql += " WHERE session_id = ?"
            params.append(session_id)
        sql += " ORDER BY created_at DESC"

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def delete_patient(self, patient_id: str, session_id: Optional[str] = None) -> bool:
        sql = "SELECT patient_id FROM patients WHERE patient_id = ?"
        params = [patient_id]
        if session_id is not None:
            sql += " AND session_id = ?"
            params.append(session_id)

        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            if not row:
                return False

            doc_rows = conn.execute("SELECT document_id FROM documents WHERE patient_id = ?", (patient_id,)).fetchall()
            for doc in doc_rows:
                conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc["document_id"],))
            conn.execute("DELETE FROM documents WHERE patient_id = ?", (patient_id,))
            cursor = conn.execute("DELETE FROM patients WHERE patient_id = ?", (patient_id,))
            return cursor.rowcount > 0
