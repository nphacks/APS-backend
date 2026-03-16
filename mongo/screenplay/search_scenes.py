from db_conn.mongo.mongo import get_db
from bson import ObjectId
from typing import Optional


def search_scenes_by_keywords(mongodb_id: str, keywords: list[str]) -> list[dict]:
    """
    Search scenes by keywords with string matching.
    Returns candidate scenes that contain any of the keywords,
    ordered by number of keyword matches (most matches first).

    Args:
        mongodb_id: MongoDB ObjectId of the screenplay
        keywords: List of keywords ranked by priority (max 5)

    Returns:
        List of dicts with scene, scene_index, matched_keywords
    """
    db = get_db()
    screenplay_collection = db["screenplays"]

    screenplay = screenplay_collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"scenes": 1}
    )

    if not screenplay or "scenes" not in screenplay:
        return []

    scenes = screenplay["scenes"]
    if not scenes:
        return []

    results = []

    for idx, scene in enumerate(scenes):
        # Build full text from all elements in the scene
        scene_text = ""
        for element in scene.get("elements", []):
            text = element.get("text", "")
            if text:
                scene_text += " " + text

        scene_text_lower = scene_text.lower()

        # Check which keywords match
        matched = []
        for kw in keywords:
            if kw.lower() in scene_text_lower:
                matched.append(kw)

        if matched:
            results.append({
                "scene": scene,
                "scene_index": idx,
                "matched_keywords": matched,
                "match_count": len(matched)
            })

    # Sort by match count descending
    results.sort(key=lambda x: x["match_count"], reverse=True)

    return results
