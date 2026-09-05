"""
Pytest configuration and global fixtures for MedLens backend test suite.
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure workspace root is on sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app import app
from backend.api.dependencies import (
    get_patient_repo,
    get_report_repo,
    get_extraction_service,
    get_summary_service,
    get_provenance_service,
    get_comparison_service,
    get_ingestion_service,
    get_llm_client,
)


@pytest.fixture(scope="session")
def client():
    """Shared FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Default test session authorization headers."""
    return {"X-Session-ID": "pytest-session-user-1"}


@pytest.fixture
def alt_auth_headers():
    """Alternative user session authorization headers for multi-tenant isolation testing."""
    return {"X-Session-ID": "pytest-session-user-2"}


@pytest.fixture
def patient_repo():
    return get_patient_repo()


@pytest.fixture
def report_repo():
    return get_report_repo()


@pytest.fixture
def extraction_service():
    return get_extraction_service()


@pytest.fixture
def summary_service():
    return get_summary_service()


@pytest.fixture
def provenance_service():
    return get_provenance_service()


@pytest.fixture
def comparison_service():
    return get_comparison_service()


@pytest.fixture
def ingestion_service():
    return get_ingestion_service()


@pytest.fixture
def llm_client():
    return get_llm_client()
