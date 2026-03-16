from typing import Optional
from db_conn.tidb.db import get_connection

def search_user_by_email_or_username(search_term: str) -> Optional[dict]:
    """Search for a user by email or username"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT id, username, email, user_type
            FROM users
            WHERE email = %s OR username = %s
            LIMIT 1
        """
        cursor.execute(query, (search_term, search_term))
        user = cursor.fetchone()
        
        return user
        
    finally:
        cursor.close()
        conn.close()
