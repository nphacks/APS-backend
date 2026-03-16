import uuid
from datetime import datetime
from passlib.context import CryptContext
from db_conn.tidb.db import get_connection
from models.tidb.user import UserRegister, UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def register_user(user_data: UserRegister) -> UserResponse:
    """Register a new user in TiDB"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            raise ValueError("Email already registered")
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (user_data.username,))
        if cursor.fetchone():
            raise ValueError("Username already taken")
        
        # Generate user ID and hash password
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(user_data.password)
        created_at = datetime.utcnow()
        
        # Insert new user
        insert_query = """
            INSERT INTO users (id, username, email, password, user_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (
            user_id,
            user_data.username,
            user_data.email,
            hashed_password,
            user_data.user_type,
            created_at
        ))
        
        conn.commit()
        
        return UserResponse(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            user_type=user_data.user_type
        )
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
