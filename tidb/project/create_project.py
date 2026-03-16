import uuid
from datetime import datetime
from db_conn.tidb.db import get_connection
from models.tidb.project import ProjectCreate, ProjectResponse

def create_project(project_data: ProjectCreate, user_id: str) -> ProjectResponse:
    """Create a new project and assign the creator as owner"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        project_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Insert project
        insert_project_query = """
            INSERT INTO projects (id, name, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_project_query, (
            project_id,
            project_data.name,
            project_data.description,
            created_at,
            created_at
        ))
        
        # Assign creator as owner
        insert_user_project_query = """
            INSERT INTO user_projects (user_id, project_id, role, added_at)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_user_project_query, (
            user_id,
            project_id,
            'owner',
            created_at
        ))
        
        # Add creation log
        insert_log_query = """
            INSERT INTO project_update_logs (project_id, log_message, created_at)
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_log_query, (
            project_id,
            "Project created",
            created_at
        ))
        
        conn.commit()
        
        return ProjectResponse(
            id=project_id,
            name=project_data.name,
            description=project_data.description,
            created_at=created_at,
            updated_at=created_at,
            user_role='owner',
            screenplay_ids=[]
        )
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
