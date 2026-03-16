from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel
from typing import List, Optional
import jwt
import os
from dotenv import load_dotenv
from models.tidb.project import ProjectCreate, ProjectUpdate, ProjectResponse
from models.tidb.user_project import UserProjectCreate, UserProjectUpdate, UserProjectResponse
from tidb.project.create_project import create_project
from tidb.project.get_projects import get_user_projects, get_project_by_id
from tidb.project.update_project import update_project
from tidb.project.delete_project import delete_project
from tidb.project.manage_project_users import (
    add_user_to_project,
    get_project_users,
    update_user_role,
    remove_user_from_project
)

load_dotenv()

router = APIRouter(prefix="/api/project", tags=["project"])

# JWT Configuration (should match authenticate_user.py)
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

# Project CRUD endpoints

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_new_project(
    project_data: ProjectCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new project"""
    try:
        return create_project(project_data, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )

@router.get("/", response_model=List[ProjectResponse])
async def get_projects(user_id: str = Depends(get_current_user_id)):
    """Get all projects for the current user"""
    try:
        return get_user_projects(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch projects: {str(e)}"
        )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get a specific project by ID"""
    try:
        return get_project_by_id(project_id, user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project: {str(e)}"
        )

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_existing_project(
    project_id: str,
    update_data: ProjectUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a project (requires owner or admin role)"""
    try:
        return update_project(project_id, user_id, update_data)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a project (requires owner role)"""
    try:
        delete_project(project_id, user_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.get("/{project_id}/info")
async def get_project_info(project_id: str):
    """
    Internal endpoint (no auth) for preprod_graph.
    Returns project name, description, and screenplay IDs.
    """
    print(f"=== project info called: project_id={project_id} ===")
    conn = None
    try:
        from db_conn.tidb.db import get_connection
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, name, description, created_at, updated_at FROM projects WHERE id = %s",
            (project_id,)
        )
        project = cursor.fetchone()
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        cursor.execute(
            "SELECT id, title, is_primary FROM screenplays WHERE project_id = %s ORDER BY is_primary DESC, created_at ASC",
            (project_id,)
        )
        screenplays = cursor.fetchall()
        cursor.close()

        return {
            "id": project["id"],
            "name": project["name"],
            "description": project["description"],
            "created_at": str(project["created_at"]),
            "updated_at": str(project["updated_at"]),
            "screenplays": [
                {"id": s["id"], "title": s["title"], "is_primary": bool(s["is_primary"])}
                for s in screenplays
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project info: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


class InternalProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


@router.patch("/{project_id}/update")
async def update_project_info_internal(project_id: str, update_data: InternalProjectUpdate):
    """
    Internal endpoint (no auth) for preprod_graph.
    Updates project name and/or description.
    """
    print(f"=== project update called: project_id={project_id}, data={update_data} ===")
    conn = None
    try:
        from db_conn.tidb.db import get_connection
        from datetime import datetime

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        update_fields = []
        params = []

        if update_data.name is not None:
            update_fields.append("name = %s")
            params.append(update_data.name)

        if update_data.description is not None:
            update_fields.append("description = %s")
            params.append(update_data.description)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = %s")
        params.append(datetime.utcnow())
        params.append(project_id)

        query = f"UPDATE projects SET {', '.join(update_fields)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()

        # Return updated project
        cursor.execute(
            "SELECT id, name, description, updated_at FROM projects WHERE id = %s",
            (project_id,)
        )
        project = cursor.fetchone()
        cursor.close()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "id": project["id"],
            "name": project["name"],
            "description": project["description"],
            "updated_at": str(project["updated_at"])
        }
    except HTTPException:
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update project: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

# User management endpoints

@router.get("/{project_id}/users", response_model=List[UserProjectResponse])
async def get_users_in_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get all users in a project"""
    try:
        return get_project_users(project_id, user_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch project users: {str(e)}"
        )

@router.post("/{project_id}/users", response_model=UserProjectResponse, status_code=status.HTTP_201_CREATED)
async def add_user(
    project_id: str,
    user_data: UserProjectCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Add a user to a project (requires owner or admin role)"""
    try:
        return add_user_to_project(project_id, user_id, user_data)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add user to project: {str(e)}"
        )

@router.patch("/{project_id}/users/{target_user_id}", response_model=UserProjectResponse)
async def update_user_role_in_project(
    project_id: str,
    target_user_id: str,
    role_data: UserProjectUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a user's role in a project (requires owner or admin role)"""
    try:
        return update_user_role(project_id, user_id, target_user_id, role_data)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user role: {str(e)}"
        )

@router.delete("/{project_id}/users/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    project_id: str,
    target_user_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Remove a user from a project (requires owner or admin role)"""
    try:
        remove_user_from_project(project_id, user_id, target_user_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove user from project: {str(e)}"
        )
