"""
Unit test untuk POST /chat  (AI chat endpoint)
"""
import pytest
from unittest.mock import MagicMock, patch

from app.ai.router import _json_load_maybe, _to_jsonable, _intent_hint


# ══════════════════════════════════════════════════════════════════════════════
#  Helper functions
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonLoadMaybe:
    def test_none_returns_empty_dict(self):
        assert _json_load_maybe(None) == {}

    def test_dict_returned_as_is(self):
        d = {"key": "value"}
        assert _json_load_maybe(d) == d

    def test_valid_json_string_parsed(self):
        assert _json_load_maybe('{"a": 1}') == {"a": 1}

    def test_invalid_string_returns_empty_dict(self):
        assert _json_load_maybe("bukan json") == {}


class TestToJsonable:
    def test_datetime_converted_to_isoformat(self):
        from datetime import datetime
        dt = datetime(2025, 12, 1, 10, 0, 0)
        result = _to_jsonable(dt)
        assert isinstance(result, str)
        assert "2025-12-01" in result

    def test_dict_recursively_converted(self):
        from datetime import datetime
        d = {"created_at": datetime(2025, 1, 1)}
        result = _to_jsonable(d)
        assert isinstance(result["created_at"], str)

    def test_list_recursively_converted(self):
        from datetime import datetime
        lst = [datetime(2025, 6, 1), "text", 42]
        result = _to_jsonable(lst)
        assert isinstance(result[0], str)
        assert result[1] == "text"
        assert result[2] == 42

    def test_primitives_unchanged(self):
        assert _to_jsonable(42)    == 42
        assert _to_jsonable("str") == "str"
        assert _to_jsonable(None)  is None


class TestIntentHint:
    def test_list_tasks_hint(self):
        assert "LIST" in _intent_hint("ada tugas apa hari ini?")
        assert "LIST" in _intent_hint("lihat tugas gue dong")

    def test_create_task_hint(self):
        assert "CREATE" in _intent_hint("buat tugas baru ya")
        assert "CREATE" in _intent_hint("bikinin tugas meeting")

    def test_delete_task_hint(self):
        assert "DELETE" in _intent_hint("hapus task yang kemarin")

    def test_edit_task_hint(self):
        assert "EDIT" in _intent_hint("ubah deskripsi tugasnya")

    def test_update_status_hint(self):
        assert "UPDATE" in _intent_hint("task laporan udah selesai")

    def test_no_keyword_returns_empty(self):
        assert _intent_hint("halo apa kabar?") == ""


# ══════════════════════════════════════════════════════════════════════════════
#  POST /chat  —  AI chat endpoint
# ══════════════════════════════════════════════════════════════════════════════

def _make_openai_response(text: str = "Sip!", tool_calls: list = None):
    """Buat mock OpenAI response."""
    mock_resp = MagicMock()
    mock_resp.output_text = text
    mock_resp.output = tool_calls or []
    return mock_resp


def _make_function_call(name: str, args: dict, call_id: str = "call-001"):
    """Buat mock function_call item dari OpenAI response."""
    import json
    item = MagicMock()
    item.type      = "function_call"
    item.name      = name
    item.arguments = json.dumps(args)
    item.call_id   = call_id
    return item


class TestChatEndpoint:
    def test_unauthorized_without_token(self):
        from tests.conftest import app
        from app.core.security import get_current_user_uid
        app.dependency_overrides.clear()

        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            response = c.post("/chat?user_message=halo")
        assert response.status_code == 401

        app.dependency_overrides[get_current_user_uid] = lambda: "uid-test-123"

    def test_chat_no_tool_called_returns_reply(self, client):
        """Model tidak memanggil tool — langsung jawab teks."""
        mock_r1 = _make_openai_response("Halo! Ada yang bisa dibantu?", tool_calls=[])
        mock_r2 = _make_openai_response("Halo! Ada yang bisa dibantu?")

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo"):
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=halo")

        assert response.status_code == 200
        assert "reply" in response.json()

    def test_chat_list_tasks_tool(self, client):
        """Model memanggil list_tasks → repo dipanggil → jawaban dikembalikan."""
        fc = _make_function_call("list_tasks", {})
        mock_r1 = _make_openai_response(tool_calls=[fc])
        mock_r2 = _make_openai_response("Kamu punya 2 tugas aktif.")

        sample_tasks = [{"id": "t1", "description": "Laporan", "status": "belum selesai"}]

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_all_tasks.return_value = sample_tasks
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=lihat tugas saya")

        assert response.status_code == 200
        assert response.json()["reply"] == "Kamu punya 2 tugas aktif."

    def test_chat_create_task_tool(self, client):
        """Model memanggil create_task → task dibuat → jawaban sukses."""
        fc = _make_function_call("create_task", {"description": "Buat slide presentasi"})
        mock_r1 = _make_openai_response(tool_calls=[fc])
        mock_r2 = _make_openai_response("Task berhasil dibuat!")

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.create_task.return_value = True
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=buat tugas buat slide")

        assert response.status_code == 200
        assert response.json()["reply"] == "Task berhasil dibuat!"

    def test_chat_update_status_tool(self, client):
        """Model memanggil update_status → status task diubah."""
        fc = _make_function_call("update_status", {"target": "laporan", "status": "selesai"})
        mock_r1 = _make_openai_response(tool_calls=[fc])
        mock_r2 = _make_openai_response("Status task diperbarui!")

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.update_status_like.return_value = True
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=laporan udah selesai")

        assert response.status_code == 200

    def test_chat_delete_task_tool(self, client):
        """Model memanggil delete_task → task dihapus."""
        fc = _make_function_call("delete_task", {"target": "slide presentasi"})
        mock_r1 = _make_openai_response(tool_calls=[fc])
        mock_r2 = _make_openai_response("Task dihapus.")

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.delete_task_like.return_value = True
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=hapus task slide")

        assert response.status_code == 200

    def test_chat_edit_task_tool(self, client):
        """Model memanggil edit_task → task diupdate."""
        fc = _make_function_call("edit_task", {
            "target": "laporan",
            "description": "Buat laporan akhir semester"
        })
        mock_r1 = _make_openai_response(tool_calls=[fc])
        mock_r2 = _make_openai_response("Task berhasil diubah.")

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.edit_task_like.return_value = True
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=ubah task laporan")

        assert response.status_code == 200

    def test_chat_fallback_when_tugas_no_tool(self, client):
        """
        Jika 'tugas' ada di pesan tapi model tidak panggil tool,
        fallback paksa list_tasks.
        """
        mock_r1 = _make_openai_response("Saya tidak mengerti.", tool_calls=[])
        mock_r2 = _make_openai_response("Kamu punya beberapa tugas.")

        sample_tasks = [{"id": "t1", "description": "Task A"}]

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_all_tasks.return_value = sample_tasks
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=ada tugas apa?")

        assert response.status_code == 200
        assert "reply" in response.json()

    def test_chat_list_tasks_filtered_by_status(self, client):
        """list_tasks dengan status filter."""
        fc = _make_function_call("list_tasks", {"status": "selesai"})
        mock_r1 = _make_openai_response(tool_calls=[fc])
        mock_r2 = _make_openai_response("Task yang sudah selesai: ...")

        all_tasks = [
            {"id": "t1", "description": "Task A", "status": "selesai"},
            {"id": "t2", "description": "Task B", "status": "belum selesai"},
        ]

        with patch("app.ai.router.client") as mock_openai, \
             patch("app.ai.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_all_tasks.return_value = all_tasks
            mock_openai.responses.create.side_effect = [mock_r1, mock_r2]
            response = client.post("/chat?user_message=task yang sudah selesai")

        assert response.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
#  GET /  —  Health check
# ══════════════════════════════════════════════════════════════════════════════

class TestRoot:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "running" in response.json()["message"].lower()
