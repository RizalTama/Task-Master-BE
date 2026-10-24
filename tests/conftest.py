"""
Shared fixtures dan patch-level setup untuk semua unit test.
Semua patching Firebase & OpenAI dilakukan SEBELUM app diimpor.
"""
import os
from unittest.mock import MagicMock, patch

# ── Env vars wajib sebelum Settings() dipanggil ──────────────────────────────
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("FIREBASE_API_KEY", "test-firebase-key")
os.environ.setdefault("JWT_SECRET_KEY", "a_very_secret_key")
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "")

# ── Patch Firebase & OpenAI sebelum modul app diimpor ────────────────────────
_mock_db = MagicMock()

_p1 = patch("firebase_admin.initialize_app")
_p2 = patch("firebase_admin.credentials.ApplicationDefault", return_value=MagicMock())
_p3 = patch("firebase_admin.firestore.client", return_value=_mock_db)
_p4 = patch("openai.OpenAI", return_value=MagicMock())

for _p in (_p1, _p2, _p3, _p4):
    _p.start()

# ── Sekarang aman untuk import app ───────────────────────────────────────────
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user_uid

# ─────────────────────────────────────────────────────────────────────────────

TEST_UID   = "uid-test-123"
TEST_EMAIL = "test@example.com"


@pytest.fixture
def client():
    """TestClient dengan dependency get_current_user_uid di-override."""
    app.dependency_overrides[get_current_user_uid] = lambda: TEST_UID
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Header Authorization dengan JWT token valid."""
    from app.core.security import create_access_token
    token = create_access_token({"sub": TEST_UID})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db():
    """Fresh MagicMock untuk Firestore DB per test."""
    return MagicMock()
