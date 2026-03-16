from db_conn.mongo.mongo import get_db
from bson import ObjectId
from typing import Optional


def get_scene_by_number(mongodb_id: str, scene_number: str) -> Optional[dict]:
    """
    Get a specific scene by scene number from a screenplay
    
    Args:
        mongodb_id: MongoDB ObjectId of the screenplay
        scene_number: Scene number (e.g., "1", "1A", "42")
    
    Returns:
        Scene dict or None if not found
    """
    db = get_db()
    screenplay_collection = db["screenplays"]
    
    screenplay = screenplay_collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"scenes": 1}
    )
    
    if not screenplay or "scenes" not in screenplay:
        return None
    
    # Find scene by scene_number
    for scene in screenplay["scenes"]:
        if scene.get("scene_number") == scene_number:
            return scene
    
    return None


def get_scene_by_position(mongodb_id: str, position: str) -> Optional[dict]:
    """
    Get a scene by position (last, first, second, third last, etc.)
    
    Args:
        mongodb_id: MongoDB ObjectId of the screenplay
        position: Position descriptor (e.g., "last", "first", "second", "third last")
    
    Returns:
        dict with 'scene' and 'scene_index' (0-based) or None if not found
    """
    db = get_db()
    screenplay_collection = db["screenplays"]
    
    screenplay = screenplay_collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"scenes": 1}
    )
    
    if not screenplay or "scenes" not in screenplay:
        return None
    
    scenes = screenplay["scenes"]
    if not scenes:
        return None
    
    # Parse position
    position_lower = position.lower().strip()
    scene_index = None
    
    # Handle "last", "first"
    if position_lower == "last":
        scene_index = len(scenes) - 1
    elif position_lower == "first":
        scene_index = 0
    else:
        # Handle "second", "third", "fourth", etc.
        ordinals = {
            "second": 1,
            "third": 2,
            "fourth": 3,
            "fifth": 4,
            "sixth": 5,
            "seventh": 6,
            "eighth": 7,
            "ninth": 8,
            "tenth": 9
        }
        
        # Check for "second last", "third last", etc.
        for ordinal, index in ordinals.items():
            if position_lower == f"{ordinal} last":
                if len(scenes) > index:
                    scene_index = len(scenes) - (index + 1)
                break
            elif position_lower == ordinal:
                if len(scenes) > index:
                    scene_index = index
                break
    
    if scene_index is None:
        return None
    
    return {
        "scene": scenes[scene_index],
        "scene_index": scene_index
    }


def get_all_scenes(mongodb_id: str) -> list[dict]:
    """
    Get all scenes from a screenplay
    
    Args:
        mongodb_id: MongoDB ObjectId of the screenplay
    
    Returns:
        List of scene dicts
    """
    db = get_db()
    screenplay_collection = db["screenplays"]
    
    screenplay = screenplay_collection.find_one(
        {"_id": ObjectId(mongodb_id)},
        {"scenes": 1}
    )
    
    if not screenplay or "scenes" not in screenplay:
        return []
    
    return screenplay["scenes"]


def format_scene_for_display(scene: dict) -> str:
    """
    Format a scene into readable text
    
    Args:
        scene: Scene dict from MongoDB
    
    Returns:
        Formatted scene text
    """
    if not scene:
        return "Scene not found"
    
    scene_number = scene.get("scene_number", "Unknown")
    elements = scene.get("elements", [])
    
    # Build scene text
    lines = [f"Scene {scene_number}"]
    lines.append("-" * 40)
    
    for element in elements:
        element_type = element.get("type", "")
        text = element.get("text", "")
        
        if element_type == "scene_heading":
            lines.append(f"\n{text.upper()}")
        elif element_type == "action":
            lines.append(f"\n{text}")
        elif element_type == "character":
            lines.append(f"\n{' ' * 20}{text.upper()}")
        elif element_type == "dialogue":
            lines.append(f"{' ' * 10}{text}")
        elif element_type == "parenthetical":
            lines.append(f"{' ' * 15}{text}")
        elif element_type == "transition":
            lines.append(f"\n{' ' * 40}{text.upper()}")
    
    return "\n".join(lines)
