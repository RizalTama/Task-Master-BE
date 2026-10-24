from fastapi import APIRouter, Depends, Request
from app.core.security import get_current_user_uid
from app.data.repo import FirestoreRepo
from .schemas import TaskCreate

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("")
def get_all_tasks(request: Request, uid: str = Depends(get_current_user_uid)):
    print("====== HEADERS RECEIVED ON /tasks ======")
    print(request.headers)
    print("========================================")
    return FirestoreRepo(user_id=uid).list_all_tasks()

@router.get("/active")
def get_active_tasks(request: Request, uid: str = Depends(get_current_user_uid)):
    print("====== HEADERS RECEIVED ON /tasks/active ======")
    print(request.headers)
    print("============================================")
    return FirestoreRepo(user_id=uid).list_active_tasks()

@router.post("")
def create_task(request: Request, payload: TaskCreate, uid: str = Depends(get_current_user_uid)):
    print("====== HEADERS RECEIVED ON /tasks (POST) ======")
    print(request.headers)
    print("==============================================")
    ok = FirestoreRepo(user_id=uid).create_task(payload.description, payload.due_date, payload.project_name)
    return {"success": ok}

@router.get("/projects")
def get_projects(request: Request, uid: str = Depends(get_current_user_uid)):
    print("====== HEADERS RECEIVED ON /tasks/projects ======")
    print(request.headers)
    print("===============================================")
    return FirestoreRepo(user_id=uid).list_projects()
