from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class BotBase(BaseModel):
    name: str
    avatar: Optional[str] = None
    greeting: Optional[str] = None
    owner_email: str

class BotCreate(BotBase):
    pass

class BotUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    greeting: Optional[str] = None

class BotResponse(BotBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
