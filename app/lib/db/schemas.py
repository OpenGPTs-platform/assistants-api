from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any, Union
from openai.types.beta.assistant import Assistant, AssistantTool
from openai.types.beta import Thread
from openai.types.beta.threads import Message
from enum import Enum

from openai.types.beta.thread_deleted import ThreadDeleted
from openai.types.beta.assistant_deleted import AssistantDeleted
from openai.types.beta.vector_store import (
    VectorStore,
    FileCounts,
    ExpiresAfter,
)
from openai.types.beta.vector_stores.vector_store_file_batch import (
    VectorStoreFileBatch,
)

from openai.pagination import SyncCursorPage
from openai.types.beta.threads import Run
from openai.types.beta.threads.runs import (
    RunStep,
    MessageCreationStepDetails,
    ToolCallsStepDetails,
)

Assistant
AssistantDeleted
Thread
ThreadDeleted
Message  # database stored message, typically used for output
SyncCursorPage
Run
RunStep
VectorStore
FileCounts,
ExpiresAfter,
VectorStoreFileBatch

StepDetails = Union[MessageCreationStepDetails, ToolCallsStepDetails]


class AssistantCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = Field(None, max_length=512)
    model: str
    instructions: Optional[str] = Field(None, max_length=32768)
    tools: List[AssistantTool] = []
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
    tools: Optional[List[AssistantTool]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)
    file_ids: Optional[List[str]] = Field(None)


class MessageContent(BaseModel):  # input for message data
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


class MessageUpdate(BaseModel):
    metadata: Optional[Dict[str, str]] = Field(default={})


class RunContent(BaseModel):
    assistant_id: str
    additional_instructions: Optional[str] = Field(default="")
    instructions: Optional[str] = Field(default="")
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    model: Optional[str] = Field(default=None)
    tools: Optional[List[AssistantTool]] = Field(default=[])
    extra_headers: Optional[Dict[str, str]] = Field(default=None)
    extra_query: Optional[Dict[str, Any]] = Field(default=None)
    extra_body: Optional[Dict[str, Any]] = Field(default=None)
    timeout: Optional[float] = Field(default=None)


class RunStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    REQUIRES_ACTION = "requires_action"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"
    EXPIRED = "expired"


class RunUpdate(BaseModel):
    assistant_id: Optional[str] = None
    cancelled_at: Optional[int] = None
    completed_at: Optional[int] = None
    expires_at: Optional[int] = None
    failed_at: Optional[int] = None
    file_ids: Optional[List[str]] = None
    instructions: Optional[str] = None
    last_error: Optional[Any] = None
    model: Optional[str] = None
    started_at: Optional[int] = None
    status: Optional[str] = None
    tools: Optional[Any] = None
    usage: Optional[Any] = None


class RunStepCreate(BaseModel):
    # Define the fields required for creating a RunStep
    assistant_id: str
    step_details: Any
    type: Literal["message_creation", "tool_calls"]
    status: Literal[
        "in_progress", "cancelled", "failed", "completed", "expired"
    ]
    step_details: StepDetails


class RunStepUpdate(BaseModel):
    assistant_id: Optional[str] = None
    cancelled_at: Optional[int] = None
    completed_at: Optional[int] = None
    expired_at: Optional[int] = None
    failed_at: Optional[int] = None
    last_error: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Literal[
        "in_progress", "cancelled", "failed", "completed", "expired"
    ] = None
    step_details: StepDetails = None
    type: Literal["message_creation", "tool_calls"] = None
    usage: Optional[Dict[str, Any]] = None


class VectorStoreCreate(BaseModel):
    file_ids: Optional[List[str]] = Field(
        default=[], description="A list of file IDs for the vector store."
    )
    name: str = Field(..., description="The name of the vector store.")
    expires_after: Optional[ExpiresAfter] = Field(
        None, description="The expiration policy for the vector store."
    )
    metadata: Optional[Dict[str, str]] = Field(
        None, description="Metadata for additional structured information."
    )


class CreateVectorStoreFileBatchRequest(BaseModel):
    file_ids: List[str] = Field(
        ..., min_items=1, max_items=500, example=["file-abc123", "file-abc456"]
    )
