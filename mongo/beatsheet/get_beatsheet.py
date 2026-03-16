from bson import ObjectId
from db_conn.mongo.mongo import get_beatsheets_collection, get_screenplays_collection


def get_beatsheet_by_screenplay(screenplay_id: str) -> dict | None:
    """
    Get beatsheet by screenplay_id.
    If no beatsheet exists and it's a version screenplay (not primary),
    fall back to the primary screenplay's beatsheet.
    """
    collection = get_beatsheets_collection()

    beatsheet = collection.find_one({"screenplay_id": screenplay_id})
    if beatsheet:
        beatsheet["_id"] = str(beatsheet["_id"])
        return beatsheet

    # Check if this is a version screenplay — fall back to primary
    screenplays_col = get_screenplays_collection()
    screenplay = screenplays_col.find_one({"_id": ObjectId(screenplay_id)})
    if screenplay and not screenplay.get("primary") and screenplay.get("primary_screenplay_id"):
        primary_id = screenplay["primary_screenplay_id"]
        beatsheet = collection.find_one({"screenplay_id": primary_id})
        if beatsheet:
            beatsheet["_id"] = str(beatsheet["_id"])
            return beatsheet

    return None
