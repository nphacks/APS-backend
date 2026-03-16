import json
import hashlib
import asyncio
from datetime import datetime
from bson import ObjectId
from db_conn.mongo.mongo import get_screenplays_collection
from utils.llm import llm_structured


def _hash_scene_elements(elements: list[dict]) -> str:
    """Create a hash of scene elements to detect changes."""
    raw = json.dumps(elements, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()


def _format_scene_text(scene: dict) -> str:
    """Convert scene elements to readable text for LLM."""
    lines = []
    for el in scene.get("elements", []):
        el_type = el.get("type", "")
        text = el.get("text", "")
        if el_type == "scene_heading":
            lines.append(f"[SCENE HEADING] {text}")
        elif el_type == "action":
            lines.append(f"[ACTION] {text}")
        elif el_type == "character":
            lines.append(f"[CHARACTER] {text}")
        elif el_type == "dialogue":
            lines.append(f"[DIALOGUE] {text}")
        elif el_type == "parenthetical":
            lines.append(f"[PARENTHETICAL] {text}")
        elif el_type == "transition":
            lines.append(f"[TRANSITION] {text}")
    return "\n".join(lines)


def detect_scenes_needing_summary(
    new_scenes: list[dict],
    existing_scenes: list[dict],
    existing_summaries: list[dict],
) -> list[dict]:
    """
    Compare new scenes against existing scenes to find which need
    summary generation. Also flags scenes missing summaries entirely.

    Returns list of scenes that need summarization.
    """
    # Build lookup of existing scene hashes
    old_hash_map = {}
    for scene in existing_scenes:
        sid = scene.get("scene_id")
        old_hash_map[sid] = _hash_scene_elements(
            scene.get("elements", [])
        )

    # Build lookup of existing summaries
    summary_map = {
        s.get("scene_id"): s.get("summary")
        for s in existing_summaries
    }

    scenes_to_summarize = []
    for scene in new_scenes:
        sid = scene.get("scene_id")
        elements = scene.get("elements", [])

        # Skip empty scenes
        if not elements:
            continue

        new_hash = _hash_scene_elements(elements)
        old_hash = old_hash_map.get(sid)

        # Needs summary if: content changed OR no summary exists
        if new_hash != old_hash or sid not in summary_map:
            scenes_to_summarize.append(scene)

    return scenes_to_summarize


def generate_scene_summary(scene: dict) -> dict:
    """
    Call LLM to generate a summary for a single scene.
    Returns { scene_id, summary }.
    """
    scene_text = _format_scene_text(scene)
    scene_id = scene.get("scene_id", "")
    scene_number = scene.get("scene_number", "")

    prompt = (
        f"Summarize this screenplay scene (Scene {scene_number}) "
        f"in 1-2 concise sentences. Focus on key plot points, "
        f"character actions, and story progression.\n\n"
        f"{scene_text}\n\n"
        f'Respond as JSON: {{"scene_id": "{scene_id}", "summary": "..."}}'
    )

    result = llm_structured(prompt, {"scene_id": "string", "summary": "string"})
    return {
        "scene_id": result.get("scene_id", scene_id),
        "summary": result.get("summary", ""),
    }


async def update_scene_summaries_async(
    mongodb_id: str,
    new_scenes: list[dict],
):
    """
    Async task: fetch existing doc, detect changed scenes,
    generate summaries, and write back to MongoDB.
    """
    collection = get_screenplays_collection()
    doc = collection.find_one({"_id": ObjectId(mongodb_id)})
    if not doc:
        return

    existing_scenes = doc.get("scenes", [])
    existing_summaries = doc.get("scene_summaries", [])

    scenes_to_summarize = detect_scenes_needing_summary(
        new_scenes, existing_scenes, existing_summaries
    )

    if not scenes_to_summarize:
        return

    # Build updated summaries list — keep existing, replace changed
    summary_map = {
        s.get("scene_id"): s.get("summary")
        for s in existing_summaries
    }

    # Generate new summaries (run in thread pool since LLM calls are blocking)
    loop = asyncio.get_event_loop()
    for scene in scenes_to_summarize:
        try:
            result = await loop.run_in_executor(
                None, generate_scene_summary, scene
            )
            summary_map[result["scene_id"]] = result["summary"]
        except Exception as e:
            print(f"Failed to summarize scene {scene.get('scene_id')}: {e}")

    # Write back
    updated_summaries = [
        {"scene_id": sid, "summary": summary}
        for sid, summary in summary_map.items()
    ]

    collection.update_one(
        {"_id": ObjectId(mongodb_id)},
        {
            "$set": {
                "scene_summaries": updated_summaries,
                "updated_at": datetime.utcnow(),
            }
        },
    )
