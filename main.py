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