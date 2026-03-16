from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection


def update_scene_at_index(mongodb_id: str, scene_index: int, scene: dict) -> dict:
    """
    Replace a scene at a specific index in the screenplay.
    Returns the updated scene with its index.
    """
    collection = get_screenplays_collection()

    # Verify the screenplay exists and index is valid
    screenplay = collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"scenes": 1}
    )

    if not screenplay:
        raise ValueError("Screenplay not found")

    scenes = screenplay.get("scenes", [])
    if scene_index < 0 or scene_index >= len(scenes):
        raise ValueError(f"Scene index {scene_index} out of range (0-{len(scenes) - 1})")

    # Update the scene at the given index
    result = collection.update_one(
        {"_id": ObjectId(mongodb_id)},
        {
            "$set": {
                f"scenes.{scene_index}": scene,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.modified_count == 0:
        raise ValueError("Failed to update scene")

    return {"scene": scene, "scene_index": scene_index}
