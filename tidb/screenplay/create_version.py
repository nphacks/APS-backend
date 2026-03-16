from datetime import datetime
from db_conn.tidb.db import get_connection
from mongo.screenplay.version_screenplay import copy_screenplay_document, get_screenplay_current_revision
from models.tidb.screenplay import ScreenplayResponse

def create_screenplay_version(parent_screenplay_id: int, user_id: str, version_title: str) -> ScreenplayResponse:
    """Create a new version by copying a primary screenplay"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get parent screenplay from TiDB
        cursor.execute(
            "SELECT mongodb_id, project_id, is_primary FROM screenplays WHERE id = %s",
            (parent_screenplay_id,)
        )
        parent = cursor.fetchone()
        
        if not parent:
            raise ValueError("Parent screenplay not found")
        
        if not parent['is_primary']:
            raise ValueError("Can only create versions from primary screenplays")
        
        # Copy screenplay in MongoDB
        version_mongodb_id = copy_screenplay_document(parent['mongodb_id'], version_title)
        
        # Get current revision from MongoDB
        current_revision = get_screenplay_current_revision(version_mongodb_id)
        
        # Create TiDB record for version
        insert_query = """
            INSERT INTO screenplays (mongodb_id, project_id, parent_id, is_primary, title, locked, current_revision, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        created_at = datetime.utcnow()
        
        cursor.execute(insert_query, (
            version_mongodb_id,
            parent['project_id'],
            parent_screenplay_id,
            False,
            version_title,
            False,
            current_revision,
            created_at,
            created_at
        ))
        
        version_id = cursor.lastrowid
        
        # Add to project_screenplays
        cursor.execute(
            "INSERT INTO project_screenplays (project_id, screenplay_id, added_at) VALUES (%s, %s, %s)",
            (parent['project_id'], version_mongodb_id, created_at)
        )
        
        conn.commit()
        
        return ScreenplayResponse(
            id=version_id,
            mongodb_id=version_mongodb_id,
            project_id=parent['project_id'],
            parent_id=parent_screenplay_id,
            is_primary=False,
            title=version_title,
            locked=False,
            current_revision=current_revision,
            created_at=created_at,
            updated_at=created_at
        )
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
