from datetime import datetime
from db_conn.tidb.db import get_connection
from mongo.screenplay.revision_screenplay import add_revision_to_document

def create_revision(
    screenplay_id: int,
    user_id: str,
    description: str,
    scenes_changed: list[str]
) -> dict:
    """Create a new revision for a locked screenplay"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get screenplay info from TiDB
        cursor.execute(
            "SELECT mongodb_id, locked, current_revision FROM screenplays WHERE id = %s",
            (screenplay_id,)
        )
        screenplay = cursor.fetchone()
        
        if not screenplay:
            raise ValueError("Screenplay not found")
        
        if not screenplay['locked']:
            raise ValueError("Screenplay must be locked before creating revisions")
        
        # Add revision to MongoDB
        revision_info = add_revision_to_document(
            mongodb_id=screenplay['mongodb_id'],
            user_id=user_id,
            description=description,
            scenes_changed=scenes_changed,
            current_revision=screenplay['current_revision']
        )
        
        # Update TiDB
        cursor.execute(
            "UPDATE screenplays SET current_revision = %s, updated_at = %s WHERE id = %s",
            (revision_info['revision_number'], datetime.utcnow(), screenplay_id)
        )
        
        conn.commit()
        
        return revision_info
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
