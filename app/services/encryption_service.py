from cryptography.fernet import Fernet
from app.config import settings
import base64

def get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY.encode()
    key = base64.urlsafe_b64encode(key[:32].ljust(32, b'0'))
    return Fernet(key)

def encrypt(data: str) -> str:
    f = get_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt(token: str) -> str:
    f = get_fernet()
    return f.decrypt(token.encode()).decode()