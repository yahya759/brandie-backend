from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.config import settings
import httpx

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://graph.instagram.com/me",
                params={"fields": "id,username", "access_token": token},
                timeout=10.0,
            )
        except httpx.RequestError:
            raise HTTPException(status_code=401, detail="تعذر الاتصال بـ Instagram")

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="توكن منتهي أو غير صالح")

    data = response.json()
    if "id" not in data:
        raise HTTPException(status_code=401, detail="توكن غير صالح")

    instagram_id = data["id"]

    user = db.query(User).filter(User.id == instagram_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="المستخدم غير موجود")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="الحساب غير نشط")

    return user