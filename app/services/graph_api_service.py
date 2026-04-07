import httpx
import asyncio
import logging
from app.config import settings
from app.services.image_service import upload_image_to_imgbb

logger = logging.getLogger(__name__)

class GraphAPIService:
    BASE_URL = "https://graph.instagram.com/v21.0"

    async def get_instagram_account_id(self, access_token: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.BASE_URL}/me",
                    params={
                        "fields": "instagram_business_account",
                        "access_token": access_token
                    }
                )
                data = response.json()
                logger.info(f"IG Account fetch response: {data}")
                
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    logger.error(f"Failed to get IG account: {error_msg}")
                    return None
                    
                ig_account = data.get("instagram_business_account", {})
                return ig_account.get("id") if isinstance(ig_account, dict) else None
        except Exception as e:
            logger.error(f"Error fetching IG account: {e}")
            return None

    async def publish_photo(self, image_path: str, caption: str) -> dict:
        access_token = settings.INSTAGRAM_ACCESS_TOKEN
        ig_account_id = settings.INSTAGRAM_ACCOUNT_ID
        
        if not access_token:
            return {"success": False, "error": "INSTAGRAM_ACCESS_TOKEN not configured"}
        
        if not ig_account_id:
            logger.info("IG_ACCOUNT_ID not configured, attempting to fetch...")
            ig_account_id = await self.get_instagram_account_id(access_token)
            if not ig_account_id:
                return {"success": False, "error": "Could not fetch Instagram Business Account ID"}
            logger.info(f"Fetched IG_ACCOUNT_ID: {ig_account_id}")

        try:
            image_url = await upload_image_to_imgbb(
                image_path,
                settings.IMGBB_API_KEY
            )
            logger.info(f"Image uploaded to: {image_url}")

            container_params = {
                "image_url": image_url,
                "caption": caption,
                "access_token": access_token
            }
            logger.info(f"Creating container with params: {container_params}")

            async with httpx.AsyncClient(timeout=30) as client:
                container_response = await client.post(
                    f"{self.BASE_URL}/{ig_account_id}/media",
                    params=container_params
                )
                logger.info(f"Container response status: {container_response.status_code}")
                logger.info(f"Container response body: {container_response.text}")
                
                if container_response.status_code != 200:
                    error_data = container_response.json()
                    error_msg = error_data.get("error", {}).get("message") or container_response.text
                    logger.error(f"Container creation HTTP {container_response.status_code}: {error_msg}")
                    return {"success": False, "error": f"فشل إنشاء المنشور: {error_msg}"}

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

                publish_params = {
                    "creation_id": container_id,
                    "access_token": access_token
                }
                logger.info(f"Publishing with params: {publish_params}")

                publish_response = await client.post(
                    f"{self.BASE_URL}/{ig_account_id}/media_publish",
                    params=publish_params
                )
                logger.info(f"Publish response status: {publish_response.status_code}")
                logger.info(f"Publish response body: {publish_response.text}")
                
                if publish_response.status_code != 200:
                    error_data = publish_response.json()
                    error_msg = error_data.get("error", {}).get("message") or publish_response.text
                    logger.error(f"Publishing HTTP {publish_response.status_code}: {error_msg}")
                    return {"success": False, "error": f"فشل النشر: {error_msg}"}

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
        access_token = settings.INSTAGRAM_ACCESS_TOKEN
        if not access_token:
            return {"valid": False, "error": "INSTAGRAM_ACCESS_TOKEN not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.BASE_URL}/me",
                    params={
                        "fields": "id,username,instagram_business_account",
                        "access_token": access_token
                    }
                )
                logger.info(f"Token check response: {response.text}")
                data = response.json()
                if "error" in data:
                    return {"valid": False, "error": data["error"]["message"]}
                
                ig_account = data.get("instagram_business_account", {})
                ig_id = ig_account.get("id") if isinstance(ig_account, dict) else None
                
                return {"valid": True, "username": data.get("username"), "ig_account_id": ig_id}
        except Exception as e:
            logger.error(f"Token check error: {e}")
            return {"valid": False, "error": str(e)}


graph_api_service = GraphAPIService()