from typing import List
from db_conn.tidb.db import get_connection
from models.tidb.project import ProjectResponse

def get_user_projects(user_id: str) -> List[ProjectResponse]:
    """Get all projects for a user"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT 
                p.id, p.name, p.description, p.created_at, p.updated_at,
                up.role as user_role
            FROM projects p
            INNER JOIN user_projects up ON p.id = up.project_id
            WHERE up.user_id = %s
            ORDER BY p.updated_at DESC
        """
        cursor.execute(query, (user_id,))
        projects = cursor.fetchall()
        
        result = []
        for project in projects:
            # Get screenplay IDs for this project
            cursor.execute(
                "SELECT screenplay_id FROM project_screenplays WHERE project_id = %s",
                (project['id'],)
            )
            screenplay_ids = [row['screenplay_id'] for row in cursor.fetchall()]
            
            result.append(ProjectResponse(
                id=project['id'],
                name=project['name'],
                description=project['description'],
                created_at=project['created_at'],
                updated_at=project['updated_at'],
                user_role=project['user_role'],
                screenplay_ids=screenplay_ids
            ))
        
        return result
        
    finally:
        cursor.close()
        conn.close()

def get_project_by_id(project_id: str, user_id: str) -> ProjectResponse:
    """Get a specific project by ID"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if user has access to this project
        query = """
            SELECT 
                p.id, p.name, p.description, p.created_at, p.updated_at,
                up.role as user_role
            FROM projects p
            INNER JOIN user_projects up ON p.id = up.project_id
            WHERE p.id = %s AND up.user_id = %s
        """
        cursor.execute(query, (project_id, user_id))
        project = cursor.fetchone()
        
        if not project:
            raise ValueError("Project not found or access denied")
        
        # Get screenplay IDs
        cursor.execute(
            "SELECT screenplay_id FROM project_screenplays WHERE project_id = %s",
            (project_id,)
        )
        screenplay_ids = [row['screenplay_id'] for row in cursor.fetchall()]
        
        return ProjectResponse(
            id=project['id'],
            name=project['name'],
            description=project['description'],
            created_at=project['created_at'],
            updated_at=project['updated_at'],
            user_role=project['user_role'],
            screenplay_ids=screenplay_ids
        )
        
    finally:
        cursor.close()
        conn.close()
