from langchain_core.tools import tool
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Post, User
from app.services.instagram_service import instagram_service
from app.services.scheduler_service import schedule_post
from app.services.graph_api_service import graph_api_service
from datetime import datetime, timedelta
import json
import re
import logging
import asyncio

logger = logging.getLogger(__name__)


@tool
def generate_caption_tool(topic: str, tone: str = "engaging") -> str:
    """Generate a professional Instagram caption with hashtags."""
    return json.dumps({
        "topic": topic,
        "tone": tone,
        "instruction": "generate_caption",
    })


@tool
def generate_image_prompt_tool(topic: str) -> str:
    """Generate an English image prompt for AI image generators (NightCafe, DALL-E, etc.)"""
    return json.dumps({
        "topic": topic,
        "instruction": "generate_image_prompt",
    })


@tool
def publish_now_tool(
    user_id: str,
    caption: str,
    hashtags: str,
    image_path: str,
) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.session_data:
            return "خطأ: لم يتم ربط حساب إنستغرام."

        full_caption = f"{caption}\n\n{hashtags}"
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                graph_api_service.publish_photo(
                    image_path=image_path,
                    caption=full_caption
                )
            )
        finally:
            loop.close()

        if result["success"]:
            post = Post(
                user_id=user_id,
                caption=caption,
                hashtags=hashtags,
                image_path=image_path,
                status="published",
                published_at=datetime.utcnow(),
            )
            db.add(post)
            db.commit()
            return "تم النشر بنجاح على إنستغرام ✅"
        else:
            return f"فشل النشر: {result['error']}"

    except Exception as e:
        logger.error(f"publish_now_tool error: {e}")
        return "حدث خطأ أثناء النشر. حاول مرة ثانية."
    finally:
        db.close()


@tool
def schedule_post_tool(
    user_id: str,
    caption: str,
    hashtags: str,
    image_path: str,
    scheduled_time_str: str,
) -> str:
    """Schedule a post to be published at a specific time."""
    db = SessionLocal()
    try:
        scheduled_at = parse_time(scheduled_time_str)
        if not scheduled_at:
            return "لم أفهم الوقت المحدد. قولي مثلاً: 'بكرا الصبح الساعة 8' أو 'الساعة 3 العصر'"

        post = Post(
            user_id=user_id,
            caption=caption,
            hashtags=hashtags,
            image_path=image_path,
            status="scheduled",
            scheduled_at=scheduled_at,
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        schedule_post(post.id, scheduled_at)

        time_formatted = scheduled_at.strftime("%Y-%m-%d الساعة %H:%M")
        return f"تم الجدولة ✅ سينشر المنشور {time_formatted}"

    except Exception as e:
        logger.error(f"schedule_post_tool error: {e}")
        return "حدث خطأ أثناء الجدولة. حاول مرة ثانية."
    finally:
        db.close()


def parse_time(time_str: str) -> datetime | None:
    now = datetime.now()
    time_str = time_str.strip().lower()

    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        pass

    base_date = now.date()
    if any(word in time_str for word in ["بكرا", "غدا", "غداً", "tomorrow"]):
        base_date = (now + timedelta(days=1)).date()

    hour_match = re.search(r'(\d{1,2})', time_str)
    if hour_match:
        hour = int(hour_match.group(1))

        if any(word in time_str for word in ["مساء", "عصر", "ليل", "pm"]):
            if hour < 12:
                hour += 12
        elif any(word in time_str for word in ["صباح", "الصبح", "am"]):
            if hour == 12:
                hour = 0

        return datetime.combine(base_date, datetime.min.time().replace(hour=hour))

    if "ساعتين" in time_str:
        return now + timedelta(hours=2)
    if "ساعة" in time_str:
        return now + timedelta(hours=1)

    return None


all_tools = [
    generate_caption_tool,
    generate_image_prompt_tool,
    publish_now_tool,
    schedule_post_tool,
]