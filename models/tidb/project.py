from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Project(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    update_logs: list[str]
    screenplay_ids: list[str]

class ProjectCreate(BaseModel):
    name: str
    description: str

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    update_log: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    user_role: str  # Role of the requesting user
    screenplay_ids: list[str]