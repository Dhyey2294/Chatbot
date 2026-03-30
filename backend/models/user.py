import uuid
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
from models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=True)   # null for Google OAuth users
    google_id = Column(String, nullable=True, unique=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
