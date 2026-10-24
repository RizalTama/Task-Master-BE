"""
Unit test untuk semua endpoint /tasks
"""
import pytest
from unittest.mock import MagicMock, patch


SAMPLE_TASKS = [
    {"id": "t1", "description": "Buat laporan", "status": "belum selesai", "project_name": "Backend"},
    {"id": "t2", "description": "Review PR",    "status": "selesai",       "project_name": "Frontend"},
]

SAMPLE_ACTIVE = [
    {"id": "t1", "description": "Buat laporan", "status": "belum selesai", "project_name": "Backend"},
]

SAMPLE_PROJECTS = [
    {"id": "p1", "name": "Backend",  "task_count": 3},
    {"id": "p2", "name": "Frontend", "task_count": 1},
]


# ══════════════════════════════════════════════════════════════════════════════
#  GET /tasks  —  List semua task
# ══════════════════════════════════════════════════════════════════════════════

class TestGetAllTasks:
    def test_returns_200_with_tasks(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_all_tasks.return_value = SAMPLE_TASKS
            response = client.get("/tasks")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["description"] == "Buat laporan"

    def test_returns_empty_list_when_no_tasks(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_all_tasks.return_value = []
            response = client.get("/tasks")

        assert response.status_code == 200
        assert response.json() == []

    def test_unauthorized_without_token(self):
        """Tanpa override dependency, token wajib ada."""
        from tests.conftest import app
        from app.core.security import get_current_user_uid
        app.dependency_overrides.clear()   # hapus override

        from fastapi.testclient import TestClient
        with TestClient(app) as c:
            response = c.get("/tasks")    # tanpa header auth
        assert response.status_code == 401

        # kembalikan override agar test lain tidak terpengaruh
        app.dependency_overrides[get_current_user_uid] = lambda: "uid-test-123"


# ══════════════════════════════════════════════════════════════════════════════
#  GET /tasks/active  —  Hanya task belum selesai
# ══════════════════════════════════════════════════════════════════════════════

class TestGetActiveTasks:
    def test_returns_200_with_active_tasks(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_active_tasks.return_value = SAMPLE_ACTIVE
            response = client.get("/tasks/active")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "belum selesai"

    def test_returns_empty_list_when_all_done(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_active_tasks.return_value = []
            response = client.get("/tasks/active")

        assert response.status_code == 200
        assert response.json() == []


# ══════════════════════════════════════════════════════════════════════════════
#  POST /tasks  —  Buat task baru
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateTask:
    def test_create_task_minimal(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.create_task.return_value = True
            response = client.post("/tasks", json={"description": "Buat dokumentasi"})

        assert response.status_code == 200
        assert response.json() == {"success": True}

    def test_create_task_with_due_date_and_project(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.create_task.return_value = True
            response = client.post("/tasks", json={
                "description": "Deploy ke production",
                "due_date":    "2025-12-31",
                "project_name": "DevOps"
            })

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_create_task_missing_description(self, client):
        response = client.post("/tasks", json={"due_date": "2025-12-01"})
        assert response.status_code == 422

    def test_create_task_repo_returns_false_on_failure(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.create_task.return_value = False
            response = client.post("/tasks", json={"description": "Task gagal"})

        assert response.status_code == 200
        assert response.json() == {"success": False}


# ══════════════════════════════════════════════════════════════════════════════
#  GET /tasks/projects  —  Daftar project beserta jumlah task
# ══════════════════════════════════════════════════════════════════════════════

class TestGetProjects:
    def test_returns_200_with_projects(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_projects.return_value = SAMPLE_PROJECTS
            response = client.get("/tasks/projects")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Backend"
        assert data[0]["task_count"] == 3

    def test_returns_empty_list_when_no_projects(self, client):
        with patch("app.tasks.router.FirestoreRepo") as MockRepo:
            MockRepo.return_value.list_projects.return_value = []
            response = client.get("/tasks/projects")

        assert response.status_code == 200
        assert response.json() == []
