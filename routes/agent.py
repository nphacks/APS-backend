from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Optional
from pydantic import BaseModel
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/agent", tags=["agent"])

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-for-development")
ALGORITHM = "HS256"

def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user ID from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        return str(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# Request/Response Models
class TextChatRequest(BaseModel):
    screenplay_id: int
    message: str
    context: Optional[dict] = None


class TextChatResponse(BaseModel):
    response: str
    conversation_id: str


class VoiceChatRequest(BaseModel):
    screenplay_id: int
    audio_data: str  # Base64 encoded audio
    context: Optional[dict] = None


class VoiceChatResponse(BaseModel):
    audio_response: str  # Base64 encoded audio
    text_transcript: str
    conversation_id: str


# Endpoints
@router.post("/text-chat", response_model=TextChatResponse)
async def text_chat(
    request: TextChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Text-based chat with preprod_graph agent
    - Handles screenplay analysis and text-based assistance
    - Routes to preprod_graph (LangGraph on Gradient AI)
    - Uses Nova Lite for reasoning
    """
    import httpx
    
    # preprod_graph agent URL (local dev or deployed)
    PREPROD_GRAPH_URL = os.getenv("PREPROD_GRAPH_URL", "http://127.0.0.1:2024")
    
    try:
        # Prepare payload for preprod_graph
        payload = {
            "assistant_id": "screenplay_agent",
            "input": {
                "screenplay_id": request.screenplay_id,
                "message": request.message,
                "response": "",
                "conversation_id": ""
            }
        }
        
        # Call preprod_graph agent
        headers = {"Content-Type": "application/json"}
        do_token = os.getenv("DIGITALOCEAN_API_TOKEN")
        if do_token:
            headers["Authorization"] = f"Bearer {do_token}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{PREPROD_GRAPH_URL}/runs/wait",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
        
        # Extract response from result
        agent_response = result.get("response", "No response from agent")
        conversation_id = result.get("conversation_id", "unknown")
        
        return TextChatResponse(
            response=agent_response,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to communicate with agent: {str(e)}"
        )


@router.post("/voice-chat", response_model=VoiceChatResponse)
async def voice_chat(
    request: VoiceChatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Voice-based chat with Gemini Live
    - DEPRECATED: Use WebSocket endpoint /voice instead
    - This endpoint kept for backward compatibility
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Voice chat moved to WebSocket endpoint /voice"
    )


@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieve conversation history
    - Returns all messages in a conversation
    - Accessible by both agents
    """
    # TODO: Implement conversation retrieval from DB
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Get conversation endpoint not yet implemented"
    )
