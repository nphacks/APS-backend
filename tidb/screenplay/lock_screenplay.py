from datetime import datetime
from db_conn.tidb.db import get_connection
from mongo.screenplay.lock_screenplay import lock_screenplay_document, unlock_screenplay_document

def lock_screenplay(screenplay_id: int, user_id: str) -> bool:
    """Lock a screenplay to prevent edits and enable revision creation"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get screenplay info from TiDB
        cursor.execute("SELECT mongodb_id, locked FROM screenplays WHERE id = %s", (screenplay_id,))
        screenplay = cursor.fetchone()
        
        if not screenplay:
            raise ValueError("Screenplay not found")
        
        if screenplay['locked']:
            raise ValueError("Screenplay is already locked")
        
        # Update MongoDB first
        lock_screenplay_document(screenplay['mongodb_id'], user_id)
        
        # Update TiDB
        cursor.execute(
            "UPDATE screenplays SET locked = TRUE, updated_at = %s WHERE id = %s",
            (datetime.utcnow(), screenplay_id)
        )
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def unlock_screenplay(screenplay_id: int) -> bool:
    """Unlock a screenplay to allow edits"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get screenplay info from TiDB
        cursor.execute("SELECT mongodb_id, locked FROM screenplays WHERE id = %s", (screenplay_id,))
        screenplay = cursor.fetchone()
        
        if not screenplay:
            raise ValueError("Screenplay not found")
        
        if not screenplay['locked']:
            raise ValueError("Screenplay is not locked")
        
        # Update MongoDB first
        unlock_screenplay_document(screenplay['mongodb_id'])
        
        # Update TiDB
        cursor.execute(
            "UPDATE screenplays SET locked = FALSE, updated_at = %s WHERE id = %s",
            (datetime.utcnow(), screenplay_id)
        )
        
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
