from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from app.config import settings
from app.database import SessionLocal
from app.models import Post
from app.services.instagram_service import instagram_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

jobstores = {
    "default": MemoryJobStore()
}

scheduler = AsyncIOScheduler(jobstores=jobstores)


def publish_scheduled_post(post_id: str):
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            logger.error(f"Post {post_id} not found")
            return

        user = post.user
        if not user.session_data:
            post.status = "failed"
            post.error_message = "لا توجد جلسة إنستغرام"
            db.commit()
            return

        result = instagram_service.publish_photo(
            encrypted_session=user.session_data,
            image_path=post.image_path,
            caption=f"{post.caption}\n\n{post.hashtags or ''}",
        )

        if result["success"]:
            post.status = "published"
            post.published_at = datetime.utcnow()
        else:
            post.status = "failed"
            post.error_message = result["error"]

        db.commit()

    except Exception as e:
        logger.error(f"Scheduler job error: {e}")
    finally:
        db.close()


def schedule_post(post_id: str, run_at: datetime):
    scheduler.add_job(
        publish_scheduled_post,
        trigger="date",
        run_date=run_at,
        args=[post_id],
        id=f"post_{post_id}",
        replace_existing=True,
    )