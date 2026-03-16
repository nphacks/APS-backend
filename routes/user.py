from fastapi import APIRouter, HTTPException, status
from models.tidb.user import UserRegister, UserLogin, TokenResponse, UserResponse
from tidb.user.register_user import register_user
from tidb.user.authenticate_user import authenticate_user
from tidb.user.search_user import search_user_by_email_or_username

router = APIRouter(prefix="/api/user", tags=["user"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """Register a new user"""
    try:
        user = register_user(user_data)
        # Auto-login after registration
        access_token, _ = authenticate_user(UserLogin(email=user_data.email, password=user_data.password))
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    """Authenticate user and return JWT token"""
    try:
        access_token, user = authenticate_user(login_data)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.get("/search", response_model=UserResponse)
async def search_user(q: str):
    """Search for a user by email or username"""
    try:
        user = search_user_by_email_or_username(q)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserResponse(**user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )
