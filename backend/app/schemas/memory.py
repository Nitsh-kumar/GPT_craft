from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List, Literal
from datetime import datetime

MemoryCategory = Literal["general", "tech_stack", "project", "preference"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class UserPreferencesUpdate(CamelModel):
    custom_instructions_profile: Optional[str] = None
    custom_instructions_style: Optional[str] = None
    memory_enabled: Optional[bool] = None


class UserPreferencesResponse(CamelModel):
    user_id: int
    custom_instructions_profile: Optional[str] = None
    custom_instructions_style: Optional[str] = None
    memory_enabled: bool = True
    updated_at: Optional[datetime] = None


class UserMemoryCreate(CamelModel):
    content: str
    category: Optional[MemoryCategory] = "general"


class UserMemoryResponse(CamelModel):
    id: int
    user_id: int
    category: MemoryCategory
    content: str
    is_active: bool
    source_conversation_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class MemoryListResponse(CamelModel):
    memories: List[UserMemoryResponse]
    total: int
    memory_enabled: bool
