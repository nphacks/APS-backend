from pydantic import BaseModel
from datetime import datetime

class Shot(BaseModel):
    shot_num: str
    shot_highlight: str
    shot_size: str # Establishing | Master | Wide | Full | Medium Full | Medium | Medium Close Up | Close Up | Extreme Close Up
    shot_framing: str # Single | Two Character | 3 or more characters | Crowd | Over the Shoulder | Point of View | Insert
    shot_angle: str # Low | High | Overhead | Dutch | Eye Level | Shoulder | Hip/Cowboy | Knee | Ground
    visual_description: str
    shot_image: str


class ShotList(BaseModel):
    screenplay_id: str # id of screenplay
    scene_id: str #scene_id from screenplay shots
    shots: list[Shot]