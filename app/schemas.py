from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date
from uuid import UUID


# ---------- USER ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    objectives: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- HABIT ----------
class HabitCreate(BaseModel):
    title: str
    description: Optional[str] = None
    frequency: str = "daily"
    category: Optional[str] = None


class HabitOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    frequency: str
    category: Optional[str]
    streak_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- TASK ----------
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    priority: str = "normal"


class TaskOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    done: bool
    due_date: Optional[date]
    priority: str
    created_at: datetime

    class Config:
        from_attributes = True

# ---------- CHANNEL ----------
class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    goal_topic: Optional[str] = None
    is_private: bool = False


class ChannelOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    goal_topic: Optional[str]
    is_private: bool
    owner_id: UUID
    created_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True    

# ---------- POST ----------
class PostCreate(BaseModel):
    channel_id: UUID
    habit_id: Optional[UUID] = None
    photo_url: str
    caption: Optional[str] = None


class PostOut(BaseModel):
    id: UUID
    channel_id: UUID
    habit_id: Optional[UUID]
    photo_url: str
    caption: Optional[str]
    ai_verified: bool
    ai_confidence_score: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

class UserSearchOut(BaseModel):
    id: UUID
    name: str
    email: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class PendingMemberOut(BaseModel):
    user_id: UUID
    name: str
    email: str
    avatar_url: Optional[str] = None 

class ReactionCreate(BaseModel):
    emoji: str


class ReactionOut(BaseModel):
    emoji: str
    count: int
    reacted_by_me: bool


class CommentCreate(BaseModel):
    text: str


class CommentOut(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_avatar: Optional[str] = None
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class PostOutFull(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_avatar: Optional[str] = None
    habit_id: Optional[UUID]
    habit_title: Optional[str] = None
    habit_streak: Optional[int] = None
    photo_url: str
    caption: Optional[str]
    ai_verified: bool
    ai_confidence_score: Optional[float]
    created_at: datetime
    reactions: list[ReactionOut] = []
    comment_count: int = 0


class RankingEntry(BaseModel):
    user_id: UUID
    name: str
    avatar_url: Optional[str] = None
    verified_count: int           