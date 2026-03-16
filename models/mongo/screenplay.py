from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class RevisionColor(str, Enum):
    WHITE = "white"          # Original
    BLUE = "blue"            # 1st revision
    PINK = "pink"            # 2nd revision
    YELLOW = "yellow"        # 3rd revision
    GREEN = "green"          # 4th revision
    GOLDENROD = "goldenrod"  # 5th revision
    BUFF = "buff"            # 6th revision
    SALMON = "salmon"        # 7th revision
    CHERRY = "cherry"        # 8th revision
    TAN = "tan"              # 9th revision

class ElementType(str, Enum):
    SCENE_HEADING = "scene_heading"
    ACTION = "action"
    CHARACTER = "character"
    DIALOGUE = "dialogue"
    PARENTHETICAL = "parenthetical"
    TRANSITION = "transition"

class SceneElement(BaseModel):
    element_id: str
    type: ElementType
    text: str
    revision_color: RevisionColor = RevisionColor.WHITE
    revision_number: int = 0
    added_in_revision: Optional[int] = None
    modified_in_revision: Optional[int] = None

class Scene(BaseModel):
    scene_id: str
    scene_number: str  # e.g., "1", "1A", "2"
    elements: list[SceneElement]
    revision_color: RevisionColor = RevisionColor.WHITE
    revision_number: int = 0
    is_new: bool = False
    is_omitted: bool = False
    added_in_revision: Optional[int] = None
    omitted_in_revision: Optional[int] = None

class Revision(BaseModel):
    revision_number: int
    revision_color: RevisionColor
    created_at: datetime
    created_by: str  # user_id
    description: str
    scenes_changed: list[str]  # List of scene_ids that changed

class UserRoles(BaseModel):
    user: str  # This is user id of existing user
    role: str  # This is owner, admin, commentator, viewer

class Screenplay(BaseModel):
    project_id: str
    primary: bool  # True for being primary screenplay and False if it is version screenplay
    primary_screenplay_id: Optional[str] = None  # Write only if primary is False
    screenplay_versions: list[str] = []  # Write this only if primary is True
    
    title: str
    written_by: list[str]
    # more title page data like contact, address
    
    scenes: list[Scene]
    
    # Revision tracking
    locked: bool = False
    locked_at: Optional[datetime] = None
    locked_by: Optional[str] = None
    current_revision: int = 0  # 0 = white (original), 1 = blue, 2 = pink, etc.
    revisions: list[Revision] = []  # History of all revisions
    
    user_roles: list[UserRoles]
    created_at: datetime
    updated_at: datetime