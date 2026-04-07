import sys
sys.dont_write_bytecode = True

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.database import init_db

from contextlib import asynccontextmanager

# Suppress noisy SQLAlchemy logs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database
    await init_db()
    yield
    # Shutdown: Add cleanup logic here if needed

app = FastAPI(title="MyChatAI API", lifespan=lifespan)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Chatbot API is running"}

from routers import bot_router, train_router, chat_router
from routers import auth_router

app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(bot_router.router)
app.include_router(train_router.router, prefix="/train", tags=["Training"])
app.include_router(chat_router.router, prefix="/chat", tags=["Chat"])
