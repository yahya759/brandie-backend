import httpx
import asyncio
import logging
from app.config import settings
from app.services.image_service import upload_image_to_imgbb

logger = logging.getLogger(__name__)

class GraphAPIService:
    BASE_URL = "https://graph.instagram.com/v21.0"

    async def publish_photo(self, image_path: str, caption: str) -> dict:
        try:
            image_url = await upload_image_to_imgbb(
                image_path,
                settings.IMGBB_API_KEY
            )
            logger.info(f"Image uploaded to: {image_url}")

            async with httpx.AsyncClient(timeout=30) as client:
                container_response = await client.post(
                    f"{self.BASE_URL}/{settings.INSTAGRAM_ACCOUNT_ID}/media",
                    params={
                        "image_url": image_url,
                        "caption": caption,
                        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
                    }
                )
                container_data = container_response.json()

                if "error" in container_data:
                    error_msg = container_data["error"].get("message", "Unknown error")
                    logger.error(f"Container creation failed: {error_msg}")
                    return {"success": False, "error": f"فشل إنشاء المنشور: {error_msg}"}

                container_id = container_data.get("id")
                if not container_id:
                    return {"success": False, "error": "لم يتم الحصول على معرف الحاوية"}

                logger.info(f"Container created: {container_id}")

                await asyncio.sleep(3)

                publish_response = await client.post(
                    f"{self.BASE_URL}/{settings.INSTAGRAM_ACCOUNT_ID}/media_publish",
                    params={
                        "creation_id": container_id,
                        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
                    }
                )
                publish_data = publish_response.json()

                if "error" in publish_data:
                    error_msg = publish_data["error"].get("message", "Unknown error")
                    logger.error(f"Publishing failed: {error_msg}")
                    return {"success": False, "error": f"فشل النشر: {error_msg}"}

                media_id = publish_data.get("id")
                logger.info(f"Published successfully: {media_id}")
                return {"success": True, "media_id": media_id}

        except Exception as e:
            logger.error(f"GraphAPI publish error: {e}")
            return {"success": False, "error": f"حدث خطأ أثناء النشر: {str(e)}"}

    async def check_token_validity(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.BASE_URL}/me",
                    params={
                        "fields": "id,username",
                        "access_token": settings.INSTAGRAM_ACCESS_TOKEN
                    }
                )
                data = response.json()
                if "error" in data:
                    return {"valid": False, "error": data["error"]["message"]}
                return {"valid": True, "username": data.get("username")}
        except Exception as e:
            return {"valid": False, "error": str(e)}


graph_api_service = GraphAPIService()