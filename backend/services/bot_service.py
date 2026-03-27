from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.bot import Bot
from schemas.bot import BotCreate, BotUpdate
from typing import List, Optional

async def create_bot(db: AsyncSession, bot_data: BotCreate) -> Bot:
    new_bot = Bot(**bot_data.model_dump())
    db.add(new_bot)
    await db.commit()
    await db.refresh(new_bot)
    return new_bot

async def get_bots(db: AsyncSession, owner_email: Optional[str] = None) -> List[Bot]:
    query = select(Bot)
    if owner_email:
        query = query.where(Bot.owner_email == owner_email)
    result = await db.execute(query)
    return result.scalars().all()

async def get_bot(db: AsyncSession, bot_id: str) -> Optional[Bot]:
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    return result.scalar_one_or_none()

async def update_bot(db: AsyncSession, bot_id: str, bot_update: BotUpdate) -> Optional[Bot]:
    bot = await get_bot(db, bot_id)
    if not bot:
        return None
    
    update_data = bot_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bot, key, value)
    
    await db.commit()
    await db.refresh(bot)
    return bot

async def delete_bot(db: AsyncSession, bot_id: str) -> bool:
    bot = await get_bot(db, bot_id)
    if not bot:
        return False
    db.delete(bot)
    await db.commit()
    return True
