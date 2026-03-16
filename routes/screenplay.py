from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import List, Optional
import jwt
import os
from dotenv import load_dotenv
from models.tidb.screenplay import ScreenplayCreate, ScreenplayResponse
from models.mongo.screenplay import Scene
from tidb.screenplay.create_screenplay import create_screenplay
from tidb.screenplay.get_screenplay import (
    get_project_screenplays,
    get_screenplay_by_id,
    get_screenplay_content,
    get_screenplay_versions
)
from tidb.screenplay.lock_screenplay import lock_screenplay, unlock_screenplay
from tidb.screenplay.create_revision import create_revision
from tidb.screenplay.create_version import create_screenplay_version
from mongo.screenplay.update_screenplay import update_screenplay_scenes
from utils.scene_summary import update_scene_summaries_async
import asyncio

load_dotenv()

router = APIRouter(prefix="/api/screenplay", tags=["screenplay"])

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
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Screenplay CRUD

@router.post("/", response_model=ScreenplayResponse, status_code=status.HTTP_201_CREATED)
async def create_new_screenplay(
    screenplay_data: ScreenplayCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new screenplay"""
    try:
        return create_screenplay(screenplay_data, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create screenplay: {str(e)}"
        )

@router.get("/project/{project_id}", response_model=List[ScreenplayResponse])
async def get_screenplays_for_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all screenplays for a project"""
    try:
        return get_project_screenplays(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch screenplays: {str(e)}"
        )

@router.get("/{screenplay_id}", response_model=ScreenplayResponse)
async def get_screenplay(
    screenplay_id: int,
    user_id: str = Depends(get_current_user_id)
):
    """Get screenplay metadata"""
    try:
        return get_screenplay_by_id(screenplay_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch screenplay: {str(e)}"
        )

@router.get("/{screenplay_id}/content")
async def get_screenplay_full_content(
    screenplay_id: int,
    user_id: str = Depends(get_current_user_id)
):
    """Get full screenplay content from MongoDB"""
    try:
        screenplay = get_screenplay_by_id(screenplay_id)
        content = get_screenplay_content(screenplay.mongodb_id)
        return content
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch screenplay content: {str(e)}"
        )

@router.get("/{screenplay_id}/versions", response_model=List[ScreenplayResponse])
async def get_versions(
    screenplay_id: int,
    user_id: str = Depends(get_current_user_id)
):
    """Get all versions of a screenplay"""
    try:
        return get_screenplay_versions(screenplay_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch versions: {str(e)}"
        )

@router.patch("/{screenplay_id}/content")
async def update_screenplay_content(
    screenplay_id: int,
    scenes: List[Scene],
    user_id: str = Depends(get_current_user_id)
):
    """Update screenplay content in MongoDB"""
    try:
        screenplay = get_screenplay_by_id(screenplay_id)
        mongodb_id = screenplay.mongodb_id

        # Convert scenes to dicts for summary detection
        scenes_as_dicts = [s.model_dump(by_alias=True) for s in scenes]

        # Fire async summary generation before overwriting scenes
        asyncio.create_task(
            update_scene_summaries_async(mongodb_id, scenes_as_dicts)
        )

        success = update_screenplay_scenes(mongodb_id, scenes)
        if success:
            return {"message": "Screenplay updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Screenplay not found"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update screenplay: {str(e)}"
        )

# Lock/Unlock

@router.post("/{screenplay_id}/lock")
async def lock(
    screenplay_id: int,
    user_id: str = Depends(get_current_user_id)
):
    """Lock a screenplay"""
    try:
        lock_screenplay(screenplay_id, user_id)
        return {"message": "Screenplay locked successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lock screenplay: {str(e)}"
        )

@router.post("/{screenplay_id}/unlock")
async def unlock(
    screenplay_id: int,
    user_id: str = Depends(get_current_user_id)
):
    """Unlock a screenplay"""
    try:
        unlock_screenplay(screenplay_id)
        return {"message": "Screenplay unlocked successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlock screenplay: {str(e)}"
        )

# Revisions

@router.post("/{screenplay_id}/revision")
async def create_new_revision(
    screenplay_id: int,
    description: str,
    scenes_changed: List[str],
    user_id: str = Depends(get_current_user_id)
):
    """Create a new revision for a locked screenplay"""
    try:
        revision = create_revision(screenplay_id, user_id, description, scenes_changed)
        return revision
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create revision: {str(e)}"
        )

# Versions

@router.post("/{screenplay_id}/version", response_model=ScreenplayResponse)
async def create_version(
    screenplay_id: int,
    version_title: str,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new version by copying the screenplay"""
    try:
        return create_screenplay_version(screenplay_id, user_id, version_title)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create version: {str(e)}"
        )
