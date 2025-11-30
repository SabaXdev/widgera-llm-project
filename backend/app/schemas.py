from datetime import datetime
from typing import List, Literal, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=72)
    password_confirm: str = Field(..., min_length=6, max_length=72)


class UserLogin(UserBase):
    password: str


class UserOut(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[UUID] = None


FieldType = Literal["string", "number"]


class FieldDefinition(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: FieldType


class ImageUploadResponse(BaseModel):
    image_id: UUID
    object_key: str
    mime_type: Optional[str]


class StructuredQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    fields: List[FieldDefinition]
    image_id: Optional[UUID] = None


class StructuredQueryResponse(BaseModel):
    result: Dict[str, Any]
    cached: bool = False
