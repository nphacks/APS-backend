from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Optional
from pydantic import BaseModel
import jwt
import os
from dotenv import load_dotenv
from mongo.screenplay.get_scenes import (
    get_scene_by_number,
    get_scene_by_position,
    get_all_scenes,
    format_scene_for_display
)
from mongo.screenplay.search_scenes import search_scenes_by_keywords
from mongo.screenplay.add_scene import get_next_scene_number, add_scene_to_screenplay
from mongo.screenplay.update_scene import update_scene_at_index

load_dotenv()

router = APIRouter(prefix="/api/screenplay/scenes", tags=["screenplay_scenes"])

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-for-development")
ALGORITHM = "HS256"


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user ID from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        return str(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


class GetSceneRequest(BaseModel):
    mongodb_id: str
    position: str  # "last", "first", "second", "third last", etc.


class GetSceneResponse(BaseModel):
    scene: dict
    formatted_text: str
    scene_index: int = -1


@router.post("/get-by-position", response_model=GetSceneResponse)
async def get_scene_by_position_endpoint(
    request: GetSceneRequest
):
    """
    Get a scene by position (last, first, second, etc.)
    Note: This endpoint is for internal use by preprod_graph (no auth required)
    """
    print(f"=== Backend get-by-position called ===")
    print(f"mongodb_id: {request.mongodb_id}")
    print(f"position: {request.position}")
    
    try:
        result = get_scene_by_position(request.mongodb_id, request.position)
        print(f"Scene retrieved: {result is not None}")
        
        if not result:
            print("Scene not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scene at position '{request.position}' not found"
            )
        
        scene = result["scene"]
        scene_index = result["scene_index"]
        formatted_text = format_scene_for_display(scene)
        print(f"Formatted text length: {len(formatted_text)}, scene_index: {scene_index}")
        
        return GetSceneResponse(
            scene=scene,
            formatted_text=formatted_text,
            scene_index=scene_index
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR in get-by-position:")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving scene: {str(e)}"
        )


@router.get("/{mongodb_id}/all")
async def get_all_scenes_endpoint(
    mongodb_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get all scenes from a screenplay
    """
    scenes = get_all_scenes(mongodb_id)
    
    return {
        "screenplay_id": mongodb_id,
        "scene_count": len(scenes),
        "scenes": scenes
    }


class SearchScenesRequest(BaseModel):
    mongodb_id: str
    keywords: list[str]


class SearchSceneResult(BaseModel):
    scene: dict
    scene_index: int
    matched_keywords: list[str]
    formatted_text: str


class SearchScenesResponse(BaseModel):
    results: list[SearchSceneResult]


@router.post("/search-by-content", response_model=SearchScenesResponse)
async def search_scenes_by_content_endpoint(request: SearchScenesRequest):
    """
    Search scenes by keyword string matching.
    Used by preprod_graph for content/dialogue-based scene lookup.
    """
    print(f"=== Backend search-by-content called ===")
    print(f"mongodb_id: {request.mongodb_id}")
    print(f"keywords: {request.keywords}")

    try:
        matches = search_scenes_by_keywords(request.mongodb_id, request.keywords)
        print(f"Found {len(matches)} matching scenes")

        results = []
        for m in matches:
            formatted = format_scene_for_display(m["scene"])
            results.append(SearchSceneResult(
                scene=m["scene"],
                scene_index=m["scene_index"],
                matched_keywords=m["matched_keywords"],
                formatted_text=formatted
            ))

        return SearchScenesResponse(results=results)
    except Exception as e:
        import traceback
        print(f"ERROR in search-by-content:")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching scenes: {str(e)}"
        )


@router.get("/next-number/{mongodb_id}")
async def get_next_scene_number_endpoint(mongodb_id: str):
    """Get the next scene number for a screenplay. Internal, no auth."""
    try:
        next_num = get_next_scene_number(mongodb_id)
        return {"next_scene_number": next_num}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting next scene number: {str(e)}"
        )


class AddSceneRequest(BaseModel):
    mongodb_id: str
    scene: dict


@router.post("/add")
async def add_scene_endpoint(request: AddSceneRequest):
    """Append a scene to the screenplay. Internal, no auth."""
    print(f"=== add scene called: mongodb_id={request.mongodb_id} ===")
    try:
        result = add_scene_to_screenplay(request.mongodb_id, request.scene)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding scene: {str(e)}"
        )


class UpdateSceneRequest(BaseModel):
    mongodb_id: str
    scene_index: int
    scene: dict


@router.put("/update")
async def update_scene_endpoint(request: UpdateSceneRequest):
    """Replace a scene at a specific index. Internal, no auth."""
    print(f"=== update scene called: mongodb_id={request.mongodb_id}, index={request.scene_index} ===")
    try:
        result = update_scene_at_index(request.mongodb_id, request.scene_index, request.scene)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating scene: {str(e)}"
        )
