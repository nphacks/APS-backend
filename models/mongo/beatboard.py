from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Union

class Group(BaseModel):
    id: str = Field(pattern=r"^\d{5}$")
    x: float
    y: float
    height: float
    width: float


class TextBlock(BaseModel):
    type: str = "text"
    value: str

class TextListBlock(BaseModel):
    type: str = "text_list"
    value: List[str]

class ImageBlock(BaseModel):
    type: str = "image"
    value: str  # base64

ContentBlock = Union[TextBlock, TextListBlock, ImageBlock]

class Sticky(BaseModel):
    id: str = Field(pattern=r"^\d{6}$")
    group_id: str # What group it belong if it does.
    x: float
    y: float
    height: float
    width: float
    content: List[ContentBlock]

class Relations(BaseModel):
    from_id: str
    to_id: str

class BeatBoard(BaseModel):
    groups: list[Group]
    stikies: list[Sticky]
    relations: list[Relations]
    create_at: datetime
    updated_at: datetime