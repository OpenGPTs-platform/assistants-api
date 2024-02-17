from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from openai.types.beta.assistant import Assistant, Tool

Assistant


class AssistantCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = Field(None, max_length=512)
    model: str
    instructions: Optional[str] = Field(None, max_length=32768)
    tools: List[Tool] = []
    file_ids: List[str] = []
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "name": "Math Tutor",
                "description": "A personal math tutor assistant.",
                "model": "gpt-4",
                "instructions": "You are a personal math tutor. When asked a question, write and run Python code to answer the question.",
                "tools": [{"type": "code_interpreter"}],
                "file_ids": [],
                "metadata": {},
            }
        }


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    profile_image: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserGpt(BaseModel):
    user_id: str
    gpt_id: str


class UserGptThread(BaseModel):
    user_id: str
    gpt_id: str
    thread_id: str

    class Config:
        orm_mode = True


class SafeUser(BaseModel):
    email: str
    name: Optional[str] = None
    profile_image: Optional[str] = None


class User(UserBase):
    id: str
    email: str
    name: Optional[str] = None
    profile_image: Optional[str] = None

    user_gpts: list[UserGpt] = []
    user_gpt_threads: list[UserGptThread] = []

    class Config:
        orm_mode = True
