from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
import jwt
import os
from dotenv import load_dotenv
from db_conn.tidb.db import get_connection
from models.tidb.user import UserLogin, UserResponse

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-for-development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(login_data: UserLogin) -> tuple[str, UserResponse]:
    """Authenticate user and return JWT token with user data"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get user by email
        cursor.execute(
            "SELECT id, username, email, password, user_type FROM users WHERE email = %s",
            (login_data.email,)
        )
        user = cursor.fetchone()
        
        if not user:
            raise ValueError("Invalid email or password")
        
        # Verify password
        if not verify_password(login_data.password, user["password"]):
            raise ValueError("Invalid email or password")
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user["id"], "email": user["email"]}
        )
        
        user_response = UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            user_type=user["user_type"]
        )
        
        return access_token, user_response
        
    finally:
        cursor.close()
        conn.close()
