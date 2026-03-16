from datetime import datetime
from db_conn.tidb.db import get_connection
from mongo.screenplay.create_screenplay import create_screenplay_document, delete_screenplay_document
from models.tidb.screenplay import ScreenplayCreate, ScreenplayResponse

def create_screenplay(screenplay_data: ScreenplayCreate, user_id: str) -> ScreenplayResponse:
    """Create a new screenplay in both TiDB and MongoDB"""
    
    # Create MongoDB document first
    try:
        mongodb_id = create_screenplay_document(
            project_id=screenplay_data.project_id,
            title=screenplay_data.title,
            user_id=user_id,
            is_primary=screenplay_data.is_primary,
            primary_screenplay_id=None
        )
    except Exception as e:
        raise Exception(f"Failed to create MongoDB document: {str(e)}")
    
    # Create TiDB record
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        insert_query = """
            INSERT INTO screenplays (mongodb_id, project_id, parent_id, is_primary, title, locked, current_revision, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        created_at = datetime.utcnow()
        
        cursor.execute(insert_query, (
            mongodb_id,
            screenplay_data.project_id,
            screenplay_data.parent_id,
            screenplay_data.is_primary,
            screenplay_data.title,
            False,
            0,
            created_at,
            created_at
        ))
        
        screenplay_id = cursor.lastrowid
        
        # Update project_screenplays table
        cursor.execute(
            "INSERT INTO project_screenplays (project_id, screenplay_id, added_at) VALUES (%s, %s, %s)",
            (screenplay_data.project_id, mongodb_id, created_at)
        )
        
        conn.commit()
        
        return ScreenplayResponse(
            id=screenplay_id,
            mongodb_id=mongodb_id,
            project_id=screenplay_data.project_id,
            parent_id=screenplay_data.parent_id,
            is_primary=screenplay_data.is_primary,
            title=screenplay_data.title,
            locked=False,
            current_revision=0,
            created_at=created_at,
            updated_at=created_at
        )
        
    except Exception as e:
        conn.rollback()
        # Rollback MongoDB insert
        delete_screenplay_document(mongodb_id)
        raise e
    finally:
        cursor.close()
        conn.close()
