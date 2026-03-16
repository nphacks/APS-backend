from db_conn.tidb.db import get_connection
from .update_project import check_permission

def delete_project(project_id: str, user_id: str) -> bool:
    """Delete a project (requires owner role only)"""
    
    # Check permissions - only owner can delete
    if not check_permission(project_id, user_id, ['owner']):
        raise PermissionError("Only project owner can delete the project")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Delete project (cascade will handle related records)
        cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        conn.commit()
        
        return cursor.rowcount > 0
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
