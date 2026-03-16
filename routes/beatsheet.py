from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel
from typing import Optional
import jwt
import os
from dotenv import load_dotenv
from mongo.beatsheet.create_beatsheet import create_beatsheet_document
from mongo.beatsheet.get_beatsheet import get_beatsheet_by_screenplay
from mongo.beatsheet.update_beatsheet import update_beatsheet_document
from utils.beatsheet_check import check_beatsheet_against_summaries
from tidb.screenplay.get_screenplay import get_screenplay_by_id
from db_conn.mongo.mongo import get_screenplays_collection
from bson import ObjectId

load_dotenv()

router = APIRouter(prefix="/api/beatsheet", tags=["beatsheet"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-for-development")
ALGORITHM = "HS256"


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


class BeatsheetCreate(BaseModel):
    screenplay_id: str
    beatsheet_columns: list[str] | None = None
    beats: list[list[str]] | None = None


class BeatsheetUpdate(BaseModel):
    beatsheet_columns: list[str]
    beats: list[list[str]]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_beatsheet(data: BeatsheetCreate, user_id: str = Depends(get_current_user_id)):
    try:
        beatsheet_id = create_beatsheet_document(data.screenplay_id, data.beatsheet_columns, data.beats)
        return {"_id": beatsheet_id, "screenplay_id": data.screenplay_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create beatsheet: {str(e)}")


@router.get("/{screenplay_id}")
async def get_beatsheet(screenplay_id: str, user_id: str = Depends(get_current_user_id)):
    try:
        beatsheet = get_beatsheet_by_screenplay(screenplay_id)
        if not beatsheet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beatsheet not found")
        return beatsheet
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get beatsheet: {str(e)}")


@router.put("/{beatsheet_id}")
async def update_beatsheet(beatsheet_id: str, data: BeatsheetUpdate, user_id: str = Depends(get_current_user_id)):
    try:
        success = update_beatsheet_document(beatsheet_id, data.beatsheet_columns, data.beats)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beatsheet not found or no changes")
        return {"message": "Beatsheet updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update beatsheet: {str(e)}")


@router.get("/{screenplay_id}/check")
async def check_beatsheet(screenplay_id: str, user_id: str = Depends(get_current_user_id)):
    """Check which beats are satisfied by existing scene summaries."""
    try:
        # Get beatsheet
        beatsheet = get_beatsheet_by_screenplay(screenplay_id)
        if not beatsheet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beatsheet not found")

        # Resolve TiDB screenplay ID to MongoDB ID
        tidb_screenplay = get_screenplay_by_id(int(screenplay_id))
        mongodb_id = tidb_screenplay.mongodb_id

        # Get screenplay scene summaries from MongoDB
        collection = get_screenplays_collection()
        screenplay = collection.find_one({"_id": ObjectId(mongodb_id)})
        if not screenplay:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenplay not found")

        scene_summaries = screenplay.get("scene_summaries", [])
        scenes = screenplay.get("scenes", [])

        # Warn if summaries are missing for some scenes
        scenes_with_elements = [s for s in scenes if s.get("elements")]
        missing_count = len(scenes_with_elements) - len(scene_summaries)

        results = check_beatsheet_against_summaries(
            beatsheet["beats"],
            beatsheet["beatsheet_columns"],
            scene_summaries,
        )

        return {
            "results": results,
            "total_scenes": len(scenes_with_elements),
            "summarized_scenes": len(scene_summaries),
            "missing_summaries": max(0, missing_count),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check beatsheet: {str(e)}",
        )


@router.get("/{screenplay_id}/brainstorm-data")
async def get_brainstorm_data(screenplay_id: str):
    """
    Internal endpoint (no auth) for preprod_graph brainstorm node.
    Takes TiDB screenplay_id, returns scene summaries + beatsheet check results.
    """
    print(f"=== brainstorm-data called: screenplay_id={screenplay_id} ===")
    try:
        # Resolve TiDB screenplay ID to MongoDB ID
        tidb_screenplay = get_screenplay_by_id(int(screenplay_id))
        mongodb_id = tidb_screenplay.mongodb_id

        # Get scene summaries from MongoDB
        collection = get_screenplays_collection()
        screenplay = collection.find_one({"_id": ObjectId(mongodb_id)})
        if not screenplay:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenplay not found")

        scene_summaries = screenplay.get("scene_summaries", [])

        # Get beatsheet check
        beatsheet = get_beatsheet_by_screenplay(screenplay_id)
        beatsheet_results = None
        beats_text = ""
        if beatsheet:
            beatsheet_results = check_beatsheet_against_summaries(
                beatsheet["beats"],
                beatsheet["beatsheet_columns"],
                scene_summaries,
            )
            # Also return raw beats for context
            for i, row in enumerate(beatsheet["beats"]):
                cols = beatsheet["beatsheet_columns"]
                row_desc = " | ".join(
                    f"{cols[j]}: {row[j]}" if j < len(cols) else row[j]
                    for j in range(len(row))
                )
                beats_text += f"Beat {i + 1}: {row_desc}\n"

        return {
            "scene_summaries": scene_summaries,
            "beatsheet_check": beatsheet_results,
            "beats_text": beats_text,
            "has_beatsheet": beatsheet is not None,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get brainstorm data: {str(e)}",
        )
