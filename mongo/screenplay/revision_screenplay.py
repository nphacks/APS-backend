from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection
from models.mongo.screenplay import Revision, RevisionColor

# Color sequence for revisions
REVISION_COLORS = [
    RevisionColor.WHITE,      # 0 - Original
    RevisionColor.BLUE,       # 1
    RevisionColor.PINK,       # 2
    RevisionColor.YELLOW,     # 3
    RevisionColor.GREEN,      # 4
    RevisionColor.GOLDENROD,  # 5
    RevisionColor.BUFF,       # 6
    RevisionColor.SALMON,     # 7
    RevisionColor.CHERRY,     # 8
    RevisionColor.TAN,        # 9
]

def get_next_revision_color(current_revision: int) -> RevisionColor:
    """Get the next color in the revision sequence"""
    next_revision = current_revision + 1
    if next_revision >= len(REVISION_COLORS):
        return REVISION_COLORS[next_revision % len(REVISION_COLORS)]
    return REVISION_COLORS[next_revision]

def add_revision_to_document(
    mongodb_id: str,
    user_id: str,
    description: str,
    scenes_changed: list[str],
    current_revision: int
) -> dict:
    """Add a revision to the screenplay document in MongoDB"""
    mongo_collection = get_screenplays_collection()
    
    next_revision = current_revision + 1
    next_color = get_next_revision_color(current_revision)
    
    revision = Revision(
        revision_number=next_revision,
        revision_color=next_color,
        created_at=datetime.utcnow(),
        created_by=user_id,
        description=description,
        scenes_changed=scenes_changed
    )
    
    result = mongo_collection.update_one(
        {"_id": ObjectId(mongodb_id)},
        {
            "$set": {
                "current_revision": next_revision,
                "updated_at": datetime.utcnow()
            },
            "$push": {
                "revisions": revision.model_dump()
            }
        }
    )
    
    if result.modified_count == 0:
        raise ValueError("Failed to add revision to screenplay")
    
    return {
        "revision_number": next_revision,
        "revision_color": next_color,
        "description": description
    }
