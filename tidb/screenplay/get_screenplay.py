from typing import List
from db_conn.tidb.db import get_connection
from mongo.screenplay.get_screenplay import get_screenplay_document
from models.tidb.screenplay import ScreenplayResponse

def get_project_screenplays(project_id: str) -> List[ScreenplayResponse]:
    """Get all screenplays for a project"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT id, mongodb_id, project_id, parent_id, is_primary, title, locked, current_revision, created_at, updated_at
            FROM screenplays
            WHERE project_id = %s
            ORDER BY is_primary DESC, created_at ASC
        """
        cursor.execute(query, (project_id,))
        screenplays = cursor.fetchall()
        
        return [ScreenplayResponse(**sp) for sp in screenplays]
        
    finally:
        cursor.close()
        conn.close()

def get_screenplay_by_id(screenplay_id: int) -> ScreenplayResponse:
    """Get a specific screenplay by TiDB ID"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT id, mongodb_id, project_id, parent_id, is_primary, title, locked, current_revision, created_at, updated_at
            FROM screenplays
            WHERE id = %s
        """
        cursor.execute(query, (screenplay_id,))
        screenplay = cursor.fetchone()
        
        if not screenplay:
            raise ValueError("Screenplay not found")
        
        return ScreenplayResponse(**screenplay)
        
    finally:
        cursor.close()
        conn.close()

def get_screenplay_content(mongodb_id: str) -> dict:
    """Get full screenplay content from MongoDB"""
    return get_screenplay_document(mongodb_id)

def get_screenplay_versions(parent_screenplay_id: int) -> List[ScreenplayResponse]:
    """Get all versions of a primary screenplay"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT id, mongodb_id, project_id, parent_id, is_primary, title, locked, current_revision, created_at, updated_at
            FROM screenplays
            WHERE parent_id = %s
            ORDER BY created_at DESC
        """
        cursor.execute(query, (parent_screenplay_id,))
        versions = cursor.fetchall()
        
        return [ScreenplayResponse(**v) for v in versions]
        
    finally:
        cursor.close()
        conn.close()
