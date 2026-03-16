from utils.llm import llm_structured


def check_beatsheet_against_summaries(
    beats: list[list[str]],
    columns: list[str],
    scene_summaries: list[dict],
) -> list[dict]:
    """
    Ask LLM to check which beats are satisfied by scene summaries.

    Returns list of { beat_index, status, reason } where status is
    'satisfied', 'partial', or 'not_started'.
    """
    # Format summaries
    summaries_text = "\n".join(
        f"- Scene {s['scene_id']}: {s['summary']}"
        for s in scene_summaries
        if s.get("summary")
    )

    if not summaries_text:
        return [
            {"beat_index": i, "status": "not_started", "reason": "No scene summaries available"}
            for i in range(len(beats))
        ]

    # Format beats
    beats_text = ""
    for i, row in enumerate(beats):
        row_desc = " | ".join(
            f"{columns[j]}: {row[j]}" if j < len(columns) else row[j]
            for j in range(len(row))
        )
        beats_text += f"Beat {i + 1}: {row_desc}\n"

    prompt = (
        "You are a screenplay development assistant. "
        "Compare the following beatsheet beats against the scene summaries "
        "and determine which beats have been written/satisfied.\n\n"
        f"SCENE SUMMARIES:\n{summaries_text}\n\n"
        f"BEATSHEET:\n{beats_text}\n\n"
        "For each beat, respond with status:\n"
        '- "satisfied": The beat is fully covered by existing scenes\n'
        '- "partial": The beat is partially covered\n'
        '- "not_started": No scenes cover this beat yet\n\n'
        "Respond as JSON:\n"
        '{"results": [{"beat_index": 0, "status": "satisfied|partial|not_started", "reason": "brief explanation"}, ...]}'
    )

    result = llm_structured(prompt, {"results": "array"})
    return result.get("results", [])
