from pydantic import BaseModel
from datetime import datetime

# screenplay_id:
#   - Screenplay id is the id beatsheet is connected to
#   - Each primary screenplay has 1 beatsheet
#   - If screenplay version has a different beatsheet then this id is updated to that. 
#   - If not then it is connected to primary screenplay id.
#   - If version screenplay does not have 

# beatsheet_columns:
#   - This is column titles ["title 1", "title 2", "title 3"]

# beats:
#   - This is array of each row for each column like [[row1col1, row1col2, row1col3] , [row2col2, row2col2, row2col3]]

class Beatsheet(BaseModel):
    screenplay_id: str 
    beatsheet_columns: list[str] 
    beats: list[list[str]] 
    create_at: datetime
    updated_at: datetime