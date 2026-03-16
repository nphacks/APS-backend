from pydantic import BaseModel
from datetime import datetime
from typing import Literal

# User roles in project
UserRole = Literal["owner", "admin", "editor", "commentator", "viewer"]

class UserProject(BaseModel):
    user_id: str
    project_id: str
    role: UserRole
    added_at: datetime

class UserProjectCreate(BaseModel):
    user_id: str
    role: UserRole

class UserProjectUpdate(BaseModel):
    role: UserRole

class UserProjectResponse(BaseModel):
    user_id: str
    username: str
    email: str
    role: UserRole
    added_at: datetime    