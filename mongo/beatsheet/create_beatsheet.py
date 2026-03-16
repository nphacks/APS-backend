from datetime import datetime
from db_conn.mongo.mongo import get_beatsheets_collection
from models.mongo.beatsheet import Beatsheet


def create_beatsheet_document(screenplay_id: str, columns: list[str] = None, beats: list[list[str]] = None) -> str:
    """Create a beatsheet document in MongoDB for a screenplay"""
    collection = get_beatsheets_collection()

    # Check if beatsheet already exists for this screenplay
    existing = collection.find_one({"screenplay_id": screenplay_id})
    if existing:
        return str(existing["_id"])

    beatsheet = Beatsheet(
        screenplay_id=screenplay_id,
        beatsheet_columns=columns or ["Act", "Beat", "Description"],
        beats=beats or [["", "", ""]],
        create_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    result = collection.insert_one(beatsheet.model_dump())
    return str(result.inserted_id)
