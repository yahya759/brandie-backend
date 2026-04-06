import json
import logging
from app.services.encryption_service import encrypt, decrypt

logger = logging.getLogger(__name__)

class InstagramService:

    def login(self, username: str, password: str) -> dict:
        """Deprecated - kept for backward compatibility"""
        return {"success": False, "error": "استخدم Instagram Graph API بدلاً من هذه الطريقة"}

    def verify_2fa(self, username: str, code: str, pending_session: str) -> dict:
        """Deprecated"""
        return {"success": False, "error": "غير مدعوم"}

    def get_client(self, encrypted_session: str):
        """Deprecated"""
        return None

    def publish_photo(self, encrypted_session: str, image_path: str, caption: str) -> dict:
        """Use graph_api_service instead"""
        import asyncio
        from app.services.graph_api_service import graph_api_service
        
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                graph_api_service.publish_photo(image_path, caption)
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            loop.close()

instagram_service = InstagramService()