from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_beatsheets_collection


def update_beatsheet_document(beatsheet_id: str, columns: list[str], beats: list[list[str]]) -> bool:
    """Update beatsheet columns and beats"""
    collection = get_beatsheets_collection()

    result = collection.update_one(
        {"_id": ObjectId(beatsheet_id)},
        {
            "$set": {
                "beatsheet_columns": columns,
                "beats": beats,
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return result.modified_count > 0
