from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection

def copy_screenplay_document(parent_mongodb_id: str, version_title: str) -> str:
    """Create a full copy of a screenplay document in MongoDB"""
    mongo_collection = get_screenplays_collection()
    
    # Get parent screenplay
    parent = mongo_collection.find_one({"_id": ObjectId(parent_mongodb_id)})
    if not parent:
        raise ValueError("Parent screenplay not found in MongoDB")
    
    # Create a full copy
    version = parent.copy()
    version.pop('_id', None)  # Remove _id to create new document
    
    # Update metadata for version
    version['primary'] = False
    version['primary_screenplay_id'] = parent_mongodb_id
    version['screenplay_versions'] = []
    version['title'] = version_title
    version['created_at'] = datetime.utcnow()
    version['updated_at'] = datetime.utcnow()
    version['locked'] = False
    version['locked_at'] = None
    version['locked_by'] = None
    
    # Insert version
    result = mongo_collection.insert_one(version)
    version_mongodb_id = str(result.inserted_id)
    
    # Update parent's screenplay_versions list
    mongo_collection.update_one(
        {"_id": ObjectId(parent_mongodb_id)},
        {
            "$push": {"screenplay_versions": version_mongodb_id},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return version_mongodb_id

def get_screenplay_current_revision(mongodb_id: str) -> int:
    """Get the current revision number from MongoDB"""
    mongo_collection = get_screenplays_collection()
    screenplay = mongo_collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"current_revision": 1}
    )
    
    if not screenplay:
        raise ValueError("Screenplay not found")
    
    return screenplay.get('current_revision', 0)
