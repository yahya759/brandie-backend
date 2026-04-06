from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, chat
from app.database import engine, Base
from app.services.scheduler_service import scheduler
from contextlib import asynccontextmanager
import os

Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    os.makedirs("uploads", exist_ok=True)
    yield
    scheduler.shutdown()

app = FastAPI(
    title="Brandie API",
    description="AI-powered Instagram automation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(chat.router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Brandie API"}


@app.get("/debug/env")
async def debug_env():
    import os
    key_names = ["OPENROUTER_API_KEY", "OPENAI_API_KEY"]
    result = {}
    for name in key_names:
        value = os.getenv(name)
        if value:
            result[name] = f"✅ Found: {name} (Starts with: {value[:7]}...)"
        else:
            result[name] = f"❌ Not Found: {name}"
    return result