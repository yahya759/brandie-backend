from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Message
from app.schemas import ChatMessageResponse
from app.agent.graph import agent
from app.dependencies import get_current_user
from langchain_core.messages import HumanMessage, AIMessage
import os
import uuid
import asyncio
import logging

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_conversation_history(db: Session, user_id: str, limit: int = 20) -> list:
    messages = (
        db.query(Message)
        .filter(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()

    result = []
    for msg in messages:
        if msg.role == "user":
            result.append(HumanMessage(content=msg.content))
        else:
            result.append(AIMessage(content=msg.content))
    return result


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    message: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_path = None

    if image and image.filename:
        if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail="صيغة الصورة غير مدعومة. استخدم JPG أو PNG أو WebP"
            )

        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        image_path = os.path.join(UPLOAD_DIR, filename)

        with open(image_path, "wb") as f:
            content = await image.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail="حجم الصورة يجب أن يكون أقل من 10MB"
                )
            f.write(content)

    user_msg = Message(
        user_id=current_user.id,
        role="user",
        content=message,
        image_url=image_path,
    )
    db.add(user_msg)
    db.commit()

    history = get_conversation_history(db, current_user.id)
    history.append(HumanMessage(content=message))

    try:
        result = await asyncio.to_thread(
            agent.invoke,
            {
                "messages": history,
                "user_id": current_user.id,
                "image_path": image_path,
                "pending_post": None,
            }
        )

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        ai_response = ai_messages[-1].content if ai_messages else "حدث خطأ. حاول مرة ثانية."

    except Exception as e:
        logger.error(f"Agent error: {e}")
        ai_response = "عذراً، حدث خطأ. حاول مرة ثانية."

    ai_msg = Message(
        user_id=current_user.id,
        role="assistant",
        content=ai_response,
    )
    db.add(ai_msg)
    db.commit()

    return ChatMessageResponse(role="assistant", content=ai_response)


@router.get("/history")
async def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    messages = (
        db.query(Message)
        .filter(Message.user_id == current_user.id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "image_url": msg.image_url,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]