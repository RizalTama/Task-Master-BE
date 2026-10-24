"""
Unit test untuk app/core/security.py
Memverifikasi pembuatan dan validasi JWT token.
"""
import pytest
from datetime import timedelta
from fastapi import HTTPException
from jose import jwt

from app.core.security import create_access_token, verify_token, get_current_user_uid
from app.core.config import settings
from app.auth.schemas import TokenData


# ══════════════════════════════════════════════════════════════════════════════
#  create_access_token
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token({"sub": "uid-abc"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_payload_subject_encoded(self):
        token = create_access_token({"sub": "uid-abc"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "uid-abc"

    def test_custom_expiry(self):
        token = create_access_token({"sub": "uid-abc"}, expires_delta=timedelta(hours=2))
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload

    def test_default_expiry_present(self):
        token = create_access_token({"sub": "uid-abc"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload


# ══════════════════════════════════════════════════════════════════════════════
#  verify_token
# ══════════════════════════════════════════════════════════════════════════════

class TestVerifyToken:
    _exc = HTTPException(status_code=401, detail="Unauthorized")

    def test_valid_token_returns_token_data(self):
        token = create_access_token({"sub": "uid-xyz"})
        result = verify_token(token, self._exc)
        assert isinstance(result, TokenData)
        assert result.uid == "uid-xyz"

    def test_invalid_token_raises_exception(self):
        with pytest.raises(HTTPException) as exc_info:
            verify_token("invalid.token.here", self._exc)
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_exception(self):
        token = create_access_token({"sub": "uid-abc"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException):
            verify_token(token, self._exc)

    def test_token_without_sub_raises_exception(self):
        # Token tanpa field 'sub'
        from datetime import datetime, timezone
        payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(HTTPException):
            verify_token(token, self._exc)
