from datetime import datetime
from db_conn.tidb.db import get_connection
from models.tidb.project import ProjectUpdate, ProjectResponse
from .get_projects import get_project_by_id

def check_permission(project_id: str, user_id: str, required_roles: list[str]) -> bool:
    """Check if user has required role for the project"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT role FROM user_projects WHERE project_id = %s AND user_id = %s",
            (project_id, user_id)
        )
        result = cursor.fetchone()
        return result and result['role'] in required_roles
    finally:
        cursor.close()
        conn.close()

def update_project(project_id: str, user_id: str, update_data: ProjectUpdate) -> ProjectResponse:
    """Update a project (requires owner or admin role)"""
    
    # Check permissions
    if not check_permission(project_id, user_id, ['owner', 'admin']):
        raise PermissionError("Only owners and admins can update projects")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        updated_at = datetime.utcnow()
        update_fields = []
        params = []
        
        if update_data.name is not None:
            update_fields.append("name = %s")
            params.append(update_data.name)
        
        if update_data.description is not None:
            update_fields.append("description = %s")
            params.append(update_data.description)
        
        if update_fields:
            update_fields.append("updated_at = %s")
            params.append(updated_at)
            params.append(project_id)
            
            query = f"UPDATE projects SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(query, params)
        
        # Add update log if provided
        if update_data.update_log:
            cursor.execute(
                "INSERT INTO project_update_logs (project_id, log_message, created_at) VALUES (%s, %s, %s)",
                (project_id, update_data.update_log, updated_at)
            )
        
        conn.commit()
        
        # Return updated project
        return get_project_by_id(project_id, user_id)
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
