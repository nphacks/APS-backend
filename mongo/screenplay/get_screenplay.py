from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection

def get_screenplay_document(mongodb_id: str) -> dict:
    """Get screenplay document from MongoDB"""
    mongo_collection = get_screenplays_collection()
    screenplay = mongo_collection.find_one({"_id": ObjectId(mongodb_id)})
    
    if not screenplay:
        raise ValueError("Screenplay not found in MongoDB")
    
    # Convert ObjectId to string for JSON serialization
    screenplay['_id'] = str(screenplay['_id'])
    return screenplay
