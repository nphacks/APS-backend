from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection

def lock_screenplay_document(mongodb_id: str, user_id: str) -> bool:
    """Lock a screenplay document in MongoDB"""
    mongo_collection = get_screenplays_collection()
    
    result = mongo_collection.update_one(
        {"_id": ObjectId(mongodb_id)},
        {
            "$set": {
                "locked": True,
                "locked_at": datetime.utcnow(),
                "locked_by": user_id,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0

def unlock_screenplay_document(mongodb_id: str) -> bool:
    """Unlock a screenplay document in MongoDB"""
    mongo_collection = get_screenplays_collection()
    
    result = mongo_collection.update_one(
        {"_id": ObjectId(mongodb_id)},
        {
            "$set": {
                "locked": False,
                "locked_at": None,
                "locked_by": None,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return result.modified_count > 0
