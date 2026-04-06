from instagrapi import Client
from instagrapi.exceptions import (
    TwoFactorRequired,
    ChallengeRequired,
    BadPassword,
    UserNotFound,
)
from app.services.encryption_service import encrypt, decrypt
from sqlalchemy.orm import Session
from app.models import User
import json
import logging

logger = logging.getLogger(__name__)

class InstagramService:

    PROXY = "http://xfodddai:phhe36pyx9ju@31.59.20.176:6754"

    def login(self, username: str, password: str) -> dict:
        cl = Client()
        cl.set_proxy(PROXY)
        cl.delay_range = [1, 3]

        try:
            cl.login(username, password)
            session_json = json.dumps(cl.get_settings())
            encrypted = encrypt(session_json)
            return {"success": True, "session": encrypted}

        except TwoFactorRequired:
            pending = json.dumps(cl.get_settings())
            return {
                "success": False,
                "requires_2fa": True,
                "pending_session": encrypt(pending),
            }

        except ChallengeRequired:
            return {
                "success": False,
                "error": "إنستغرام يطلب تحقق إضافي. افتح التطبيق على هاتفك وأكّد تسجيل الدخول.",
            }

        except BadPassword:
            return {"success": False, "error": "كلمة المرور غير صحيحة."}

        except UserNotFound:
            return {"success": False, "error": "اسم المستخدم غير موجود."}

        except Exception as e:
            logger.error(f"Instagram login error: {e}")
            return {"success": False, "error": "حدث خطأ أثناء تسجيل الدخول. حاول مرة ثانية."}

    def verify_2fa(self, username: str, code: str, pending_session: str) -> dict:
        cl = Client()
        try:
            settings = json.loads(decrypt(pending_session))
            cl.set_settings(settings)
            cl.login(username, verification_code=code)
            session_json = json.dumps(cl.get_settings())
            return {"success": True, "session": encrypt(session_json)}
        except Exception as e:
            logger.error(f"2FA error: {e}")
            return {"success": False, "error": "رمز التحقق غير صحيح."}

    def get_client(self, encrypted_session: str) -> Client:
        cl = Client()
        cl.set_proxy(PROXY)
        cl.delay_range = [1, 3]
        session_json = decrypt(encrypted_session)
        cl.set_settings(json.loads(session_json))
        return cl

    def publish_photo(self, encrypted_session: str, image_path: str, caption: str) -> dict:
        import asyncio
        from app.services.graph_api_service import graph_api_service
        
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                graph_api_service.publish_photo(image_path, caption)
            )
            return result
        finally:
            loop.close()


instagram_service = InstagramService()