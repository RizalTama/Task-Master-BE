"""
Unit test untuk POST /auth/register dan POST /auth/login
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import httpx


# ══════════════════════════════════════════════════════════════════════════════
#  POST /auth/register
# ══════════════════════════════════════════════════════════════════════════════

class TestRegister:
    def test_register_success(self, client):
        mock_user = MagicMock()
        mock_user.uid   = "new-uid-001"
        mock_user.email = "user@example.com"
        mock_user.user_metadata.creation_timestamp = 1700000000000

        with patch("app.auth.router.auth.create_user", return_value=mock_user), \
             patch("app.auth.router.FirestoreRepo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.db.collection.return_value.document.return_value.set.return_value = None

            response = client.post("/auth/register", json={
                "email": "user@example.com",
                "password": "password123"
            })

        assert response.status_code == 201
        data = response.json()
        assert data["uid"] == "new-uid-001"
        assert data["email"] == "user@example.com"

    def test_register_email_already_exists(self, client):
        import firebase_admin.auth as fb_auth

        with patch("app.auth.router.auth.create_user",
                   side_effect=fb_auth.EmailAlreadyExistsError("", "", "")):
            response = client.post("/auth/register", json={
                "email": "existing@example.com",
                "password": "password123"
            })

        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]

    def test_register_invalid_email_format(self, client):
        response = client.post("/auth/register", json={
            "email": "bukan-email",
            "password": "password123"
        })
        assert response.status_code == 422   # Pydantic validation error

    def test_register_missing_password(self, client):
        response = client.post("/auth/register", json={"email": "user@example.com"})
        assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
#  POST /auth/login
# ══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    def _mock_firebase_response(self):
        """Buat mock response sukses dari Firebase REST API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"localId": "uid-from-firebase"}
        mock_response.raise_for_status = MagicMock()
        return mock_response

    def test_login_success(self, client):
        mock_http_response = self._mock_firebase_response()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__  = AsyncMock(return_value=False)
        mock_async_client.post       = AsyncMock(return_value=mock_http_response)

        with patch("app.auth.router.httpx.AsyncClient", return_value=mock_async_client):
            response = client.post("/auth/login", json={
                "email": "user@example.com",
                "password": "password123"
            })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["uid"] == "uid-from-firebase"
        assert data["user"]["email"] == "user@example.com"

    def test_login_wrong_credentials(self, client):
        mock_error_response = MagicMock()
        mock_error_response.json.return_value = {
            "error": {"message": "INVALID_PASSWORD"}
        }
        http_error = httpx.HTTPStatusError(
            "401", request=MagicMock(), response=mock_error_response
        )

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__  = AsyncMock(return_value=False)
        mock_async_client.post       = AsyncMock(side_effect=http_error)

        with patch("app.auth.router.httpx.AsyncClient", return_value=mock_async_client):
            response = client.post("/auth/login", json={
                "email": "user@example.com",
                "password": "wrongpassword"
            })

        assert response.status_code == 401
        assert response.json()["detail"] == "INVALID_PASSWORD"

    def test_login_missing_fields(self, client):
        response = client.post("/auth/login", json={"email": "user@example.com"})
        assert response.status_code == 422
