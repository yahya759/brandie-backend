import httpx
import base64
import logging

logger = logging.getLogger(__name__)

async def upload_image_to_imgbb(image_path: str, imgbb_api_key: str) -> str:
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.imgbb.com/1/upload",
                data={
                    "key": imgbb_api_key,
                    "image": image_data,
                    "expiration": 600
                }
            )
            data = response.json()

            if not data.get("success"):
                raise Exception(f"imgbb upload failed: {data}")

            return data["data"]["url"]

    except Exception as e:
        logger.error(f"Image upload error: {e}")
        raise