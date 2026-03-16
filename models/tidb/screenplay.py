from typing import Optional
from pydantic import Field, model_validator
from pydantic import BaseModel
from datetime import datetime

class ScreenplayCreate(BaseModel):
    mongodb_id: Optional[str] = Field(None, max_length=64)
    project_id: str
    parent_id: Optional[int] = None
    is_primary: bool
    title: str

    @model_validator(mode="after")
    def validate_relationship(self):
        if self.is_primary and self.parent_id is not None:
            raise ValueError("Primary screenplay cannot have parent_id")
        if not self.is_primary and self.parent_id is None:
            raise ValueError("Version screenplay must have parent_id")
        return self

class ScreenplayResponse(BaseModel):
    id: int
    mongodb_id: str
    project_id: str
    parent_id: Optional[int]
    is_primary: bool
    title: str
    locked: bool
    current_revision: int
    created_at: datetime
    updated_at: datetime