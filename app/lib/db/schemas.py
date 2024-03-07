from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from openai.types.beta.assistant import Assistant, Tool
from openai.types.beta import Thread
from openai.types.beta.assistant_deleted import AssistantDeleted

Assistant
AssistantDeleted
Thread


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
                "instructions": "You are a personal math tutor. When asked a question, write and run Python code to answer the question.",  # noqa
                "tools": [{"type": "code_interpreter"}],
                "file_ids": [],
                "metadata": {},
            }
        }


class AssistantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = Field(None, max_length=512)
    model: Optional[str] = Field(None, max_length=256)
    instructions: Optional[str] = Field(None, max_length=32768)
    tools: Optional[List[Tool]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)
    file_ids: Optional[List[str]] = Field(None)


class MessageContent(BaseModel):
    role: str
    content: str
    file_ids: Optional[List[str]] = Field(default=[])
    metadata: Optional[Dict[str, str]] = Field(default={})


class ThreadCreate(BaseModel):
    messages: Optional[List[MessageContent]] = Field(default=[])
    metadata: Optional[Dict[str, str]] = Field(default={})


class ThreadUpdate(BaseModel):
    messages: Optional[List[MessageContent]] = Field(default=[])
    metadata: Optional[Dict[str, str]] = Field(default={})
