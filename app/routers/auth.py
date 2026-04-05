from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import InstagramLoginRequest, TokenResponse, TwoFactorRequest
from app.services.instagram_service import instagram_service
from app.config import settings
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


@router.post("/instagram/login", response_model=dict)
async def instagram_login(
    request: InstagramLoginRequest,
    db: Session = Depends(get_db),
):
    result = instagram_service.login(request.username, request.password)

    if result.get("requires_2fa"):
        return {
            "requires_2fa": True,
            "pending_session": result["pending_session"],
            "message": "أدخل رمز التحقق المرسل لهاتفك",
        }

    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "فشل تسجيل الدخول"))

    user = db.query(User).filter(
        User.instagram_username == request.username
    ).first()

    if not user:
        user = User(
            instagram_username=request.username,
            session_data=result["session"],
        )
        db.add(user)
    else:
        user.session_data = result["session"]

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/instagram/verify-2fa", response_model=dict)
async def verify_2fa(
    request: TwoFactorRequest,
    db: Session = Depends(get_db),
):
    result = instagram_service.verify_2fa(
        username=request.username,
        code=request.verification_code,
        pending_session=request.pending_session,
    )

    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error"))

    user = db.query(User).filter(
        User.instagram_username == request.username
    ).first()

    if not user:
        user = User(
            instagram_username=request.username,
            session_data=result["session"],
        )
        db.add(user)
    else:
        user.session_data = result["session"]

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return {"access_token": token, "token_type": "bearer"}