from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class User(BaseModel):
    id: str
    username: str
    email: str
    password: str
    user_type: str # Individual or Organization
    created_at: datetime

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    user_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    user_type: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse