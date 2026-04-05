from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InstagramLoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TwoFactorRequest(BaseModel):
    username: str
    verification_code: str
    pending_session: str

class ChatMessageRequest(BaseModel):
    message: str
    image_base64: Optional[str] = None

class ChatMessageResponse(BaseModel):
    role: str
    content: str
    image_url: Optional[str] = None
    action_taken: Optional[str] = None

class PostResponse(BaseModel):
    id: str
    caption: str
    hashtags: Optional[str]
    status: str
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True