from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    OPENAI_API_KEY: str = "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"
    ENCRYPTION_KEY: str
    INSTAGRAM_ACCESS_TOKEN: str = ""
    INSTAGRAM_ACCOUNT_ID: str = ""
    IMGBB_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    HF_SPACE_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

AVAILABLE_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free", 
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
    "deepseek/deepseek-r1-distill-llama-70b:free",
    "microsoft/phi-3-medium-128k-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]

current_model_index = 0