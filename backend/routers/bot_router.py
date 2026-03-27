from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_db
from schemas.bot import BotCreate, BotUpdate, BotResponse
from services import bot_service
from typing import List

router = APIRouter(prefix="/bots", tags=["Bots"])

@router.post("/", response_model=BotResponse)
async def create_new_bot(bot: BotCreate, db: AsyncSession = Depends(get_db)):
    return await bot_service.create_bot(db, bot)

@router.get("/", response_model=List[BotResponse])
async def list_bots(owner_email: str = None, db: AsyncSession = Depends(get_db)):
    return await bot_service.get_bots(db, owner_email)

@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot_by_id(bot_id: str, db: AsyncSession = Depends(get_db)):
    bot = await bot_service.get_bot(db, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot

@router.patch("/{bot_id}", response_model=BotResponse)
async def update_existing_bot(bot_id: str, bot_update: BotUpdate, db: AsyncSession = Depends(get_db)):
    bot = await bot_service.update_bot(db, bot_id, bot_update)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot

@router.delete("/{bot_id}")
async def delete_existing_bot(bot_id: str, db: AsyncSession = Depends(get_db)):
    success = await bot_service.delete_bot(db, bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"message": "Bot deleted successfully"}
