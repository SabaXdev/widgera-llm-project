from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped
import uuid

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    username: Mapped[str] = Column(String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = Column(String(255), nullable=False)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    images: Mapped[list["Image"]] = relationship("Image", back_populates="user")


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (UniqueConstraint("user_id", "content_hash", name="uq_user_hash"),)

    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    user_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    object_key: Mapped[str] = Column(String(255), nullable=False, unique=True)
    mime_type: Mapped[Optional[str]] = Column(String(100))
    content_hash: Mapped[str] = Column(String(128), nullable=False)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="images")


class QueryCache(Base):
    __tablename__ = "query_cache"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    cache_key: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    prompt: Mapped[str] = Column(Text, nullable=False)
    field_schema_json: Mapped[str] = Column(Text, nullable=False)
    image_hash: Mapped[Optional[str]] = Column(String(128))
    response_json: Mapped[str] = Column(Text, nullable=False)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
