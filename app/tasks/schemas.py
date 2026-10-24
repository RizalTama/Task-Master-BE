from pydantic import BaseModel
from typing import Optional

class TaskCreate(BaseModel):
    description: str
    due_date: Optional[str] = None
    project_name: Optional[str] = None
