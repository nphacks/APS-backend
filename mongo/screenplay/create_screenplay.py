from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection
from models.mongo.screenplay import Screenplay, UserRoles

def create_screenplay_document(
    project_id: str,
    title: str,
    user_id: str,
    is_primary: bool = True,
    primary_screenplay_id: str = None
) -> str:
    """Create a screenplay document in MongoDB"""
    mongo_collection = get_screenplays_collection()
    
    screenplay = Screenplay(
        project_id=project_id,
        primary=is_primary,
        primary_screenplay_id=primary_screenplay_id,
        screenplay_versions=[],
        title=title,
        written_by=[user_id],
        scenes=[],
        locked=False,
        locked_at=None,
        locked_by=None,
        current_revision=0,
        revisions=[],
        user_roles=[UserRoles(user=user_id, role="owner")],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    result = mongo_collection.insert_one(screenplay.model_dump(by_alias=True))
    return str(result.inserted_id)

def delete_screenplay_document(mongodb_id: str) -> bool:
    """Delete a screenplay document from MongoDB"""
    mongo_collection = get_screenplays_collection()
    result = mongo_collection.delete_one({"_id": ObjectId(mongodb_id)})
    return result.deleted_count > 0
