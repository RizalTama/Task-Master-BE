"""
Unit test untuk app/data/repo.py
FirestoreRepo di-test dengan Firestore client yang di-mock.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from app.data.repo import FirestoreRepo, parse_due_date_any, _parse_date


# ── Helper: buat mock document snapshot ──────────────────────────────────────

class _Doc:
    """Simulasi Firestore document snapshot."""
    def __init__(self, doc_id: str, data: dict):
        self.id = doc_id
        self._data = data
        self.reference = MagicMock()

    def to_dict(self):
        return self._data.copy()


def _make_repo(mock_db: MagicMock) -> FirestoreRepo:
    with patch("app.data.repo.firestore.client", return_value=mock_db):
        return FirestoreRepo(user_id="uid-test")


# ══════════════════════════════════════════════════════════════════════════════
#  parse_due_date_any
# ══════════════════════════════════════════════════════════════════════════════

class TestParseDueDateAny:
    def test_iso_date_string(self):
        result = parse_due_date_any("2025-12-25")
        assert isinstance(result, datetime)

    def test_indonesian_date(self):
        result = parse_due_date_any("14 November 2025")
        assert isinstance(result, datetime)
        assert result.month == 11

    def test_none_returns_none(self):
        assert parse_due_date_any(None) is None

    def test_empty_string_returns_none(self):
        assert parse_due_date_any("") is None


# ══════════════════════════════════════════════════════════════════════════════
#  _parse_date (legacy parser)
# ══════════════════════════════════════════════════════════════════════════════

class TestParseDateLegacy:
    def test_yyyy_mm_dd(self):
        result = _parse_date("2025-11-07")
        assert result.year == 2025
        assert result.month == 11

    def test_dd_month_yyyy(self):
        result = _parse_date("07 November 2025")
        assert result.day == 7
        assert result.month == 11

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            _parse_date("not-a-date")


# ══════════════════════════════════════════════════════════════════════════════
#  FirestoreRepo.create_task
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateTask:
    def test_create_task_minimal(self):
        db = MagicMock()
        repo = _make_repo(db)
        result = repo.create_task("Buat laporan", None, None)
        assert result is True
        db.collection.return_value.document.return_value.collection.return_value.add.assert_called_once()

    def test_create_task_with_due_date(self):
        db = MagicMock()
        repo = _make_repo(db)
        result = repo.create_task("Meeting", "2025-12-01", None)
        assert result is True

    def test_create_task_with_project(self):
        db = MagicMock()
        # ensure_project: query returns empty (project belum ada)
        db.collection.return_value.document.return_value.collection.return_value \
          .where.return_value.limit.return_value.stream.return_value = iter([])
        repo = _make_repo(db)
        result = repo.create_task("Deploy app", None, "Backend")
        assert result is True

    def test_create_task_invalid_due_date_raises(self):
        db = MagicMock()
        repo = _make_repo(db)
        with pytest.raises(ValueError):
            repo.create_task("Task", "bukan-tanggal-valid-xyz", None)


# ══════════════════════════════════════════════════════════════════════════════
#  FirestoreRepo.list_all_tasks
# ══════════════════════════════════════════════════════════════════════════════

class TestListAllTasks:
    def test_returns_list_with_tasks(self):
        db = MagicMock()
        proj_doc = _Doc("proj-1", {"name": "Backend"})
        task_doc = _Doc("task-1", {"description": "Fix bug", "status": "belum selesai", "project_id": "proj-1"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.side_effect = [iter([proj_doc]), iter([task_doc])]

        repo = _make_repo(db)
        result = repo.list_all_tasks()

        assert len(result) == 1
        assert result[0]["description"] == "Fix bug"
        assert result[0]["project_name"] == "Backend"

    def test_task_without_project_returns_none_project_name(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Task tanpa project", "status": "belum selesai"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.side_effect = [iter([]), iter([task_doc])]

        repo = _make_repo(db)
        result = repo.list_all_tasks()

        assert result[0]["project_name"] is None

    def test_returns_empty_list_when_no_tasks(self):
        db = MagicMock()
        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.side_effect = [iter([]), iter([])]

        repo = _make_repo(db)
        result = repo.list_all_tasks()
        assert result == []


# ══════════════════════════════════════════════════════════════════════════════
#  FirestoreRepo.list_active_tasks
# ══════════════════════════════════════════════════════════════════════════════

class TestListActiveTasks:
    def test_returns_only_active_tasks(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Tugas aktif", "status": "belum selesai"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.return_value = iter([])                  # projects
        col.where.return_value.stream.return_value = iter([task_doc])  # active tasks

        repo = _make_repo(db)
        result = repo.list_active_tasks()

        assert len(result) == 1
        assert result[0]["status"] == "belum selesai"


# ══════════════════════════════════════════════════════════════════════════════
#  FirestoreRepo.update_status_like
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateStatusLike:
    def test_updates_matching_task(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Buat laporan bulanan", "status": "belum selesai"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.return_value = iter([task_doc])

        repo = _make_repo(db)
        result = repo.update_status_like("laporan", "selesai")

        assert result is True
        task_doc.reference.update.assert_called_once()

    def test_no_match_returns_false(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Unrelated task"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.return_value = iter([task_doc])

        repo = _make_repo(db)
        result = repo.update_status_like("laporan", "selesai")
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
#  FirestoreRepo.edit_task_like
# ══════════════════════════════════════════════════════════════════════════════

class TestEditTaskLike:
    def test_edits_matching_task_description(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Meeting dengan klien"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.return_value = iter([task_doc])

        repo = _make_repo(db)
        result = repo.edit_task_like("Meeting", {"description": "Meeting dengan tim internal"})

        assert result is True
        task_doc.reference.update.assert_called_once()

    def test_no_match_raises_value_error(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Task lain"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.return_value = iter([task_doc])

        repo = _make_repo(db)
        with pytest.raises(ValueError, match="tidak ditemukan"):
            repo.edit_task_like("Meeting", {"description": "New desc"})


# ══════════════════════════════════════════════════════════════════════════════
#  FirestoreRepo.delete_task_like
# ══════════════════════════════════════════════════════════════════════════════

class TestDeleteTaskLike:
    def test_deletes_matching_task(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Hapus task ini"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.return_value = iter([task_doc])

        repo = _make_repo(db)
        result = repo.delete_task_like("Hapus task")

        assert result is True
        task_doc.reference.delete.assert_called_once()

    def test_no_match_returns_false(self):
        db = MagicMock()
        task_doc = _Doc("task-1", {"description": "Task tidak cocok"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.stream.return_value = iter([task_doc])

        repo = _make_repo(db)
        result = repo.delete_task_like("keyword tidak ada")
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
#  FirestoreRepo.ensure_project
# ══════════════════════════════════════════════════════════════════════════════

class TestEnsureProject:
    def test_returns_none_for_empty_name(self):
        db = MagicMock()
        repo = _make_repo(db)
        assert repo.ensure_project("") is None
        assert repo.ensure_project(None) is None

    def test_returns_existing_project_id(self):
        db = MagicMock()
        existing_doc = _Doc("proj-existing", {"name": "Backend", "name_lower": "backend"})

        col = db.collection.return_value.document.return_value.collection.return_value
        col.where.return_value.limit.return_value.stream.return_value = iter([existing_doc])

        repo = _make_repo(db)
        result = repo.ensure_project("Backend")
        assert result == "proj-existing"

    def test_creates_new_project_if_not_exists(self):
        db = MagicMock()
        col = db.collection.return_value.document.return_value.collection.return_value
        col.where.return_value.limit.return_value.stream.return_value = iter([])
        new_ref = MagicMock()
        new_ref.id = "proj-new"
        col.document.return_value = new_ref

        repo = _make_repo(db)
        result = repo.ensure_project("Frontend")
        assert result == "proj-new"
        new_ref.set.assert_called_once()
