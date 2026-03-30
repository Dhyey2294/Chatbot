from pydantic import BaseModel, Field, field_serializer
from datetime import datetime, timezone
from typing import Optional

class BotBase(BaseModel):
    name: str
    avatar: Optional[str] = None
    greeting: Optional[str] = None
    owner_email: Optional[str] = None

class BotCreate(BotBase):
    pass

class BotUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    greeting: Optional[str] = None

class BotResponse(BotBase):
    id: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True
