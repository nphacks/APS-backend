from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection
from models.mongo.screenplay import Scene

def update_screenplay_scenes(mongodb_id: str, scenes: list[Scene]) -> bool:
    """Update screenplay scenes in MongoDB"""
    mongo_collection = get_screenplays_collection()
    
    result = mongo_collection.update_one(
        {"_id": ObjectId(mongodb_id)},
        {
            "$set": {
                "scenes": [scene.model_dump(by_alias=True) for scene in scenes],
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0
