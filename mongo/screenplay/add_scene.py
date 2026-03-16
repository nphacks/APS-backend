from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection


def get_next_scene_number(mongodb_id: str) -> str:
    """Get the next scene number for a screenplay."""
    collection = get_screenplays_collection()
    screenplay = collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"scenes": 1}
    )

    if not screenplay or "scenes" not in screenplay:
        return "1"

    scenes = screenplay["scenes"]
    if not scenes:
        return "1"

    # Find the highest numeric scene number
    max_num = 0
    for scene in scenes:
        sn = scene.get("scene_number", "0")
        try:
            num = int(sn.rstrip("ABCDEFGHIJ"))
            if num > max_num:
                max_num = num
        except ValueError:
            pass

    return str(max_num + 1)


def add_scene_to_screenplay(mongodb_id: str, scene: dict) -> dict:
    """
    Append a scene to the end of a screenplay.
    Returns the scene with its index.
    """
    collection = get_screenplays_collection()

    result = collection.update_one(
        {"_id": ObjectId(mongodb_id)},
        {
            "$push": {"scenes": scene},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    if result.modified_count == 0:
        raise ValueError("Screenplay not found or scene not added")

    # Get the new scene index
    screenplay = collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"scenes": 1}
    )
    scene_index = len(screenplay["scenes"]) - 1

    return {"scene": scene, "scene_index": scene_index}
