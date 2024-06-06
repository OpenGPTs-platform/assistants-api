from pydantic import BaseModel, Field
from typing import Iterable, Literal, Optional, List, Dict, Any, Union
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
from openai.types.beta.threads.message_create_params import Attachment
from openai.types.beta import assistant_update_params, assistant_create_params
from openai.types.beta.threads.runs import (
    RunStep,
    MessageCreationStepDetails,
    ToolCallsStepDetails,
)
from openai.types.beta.threads.run_submit_tool_outputs_params import ToolOutput
from openai.types.beta.threads.run import Run, RequiredAction
from openai.types.beta.threads.text_content_block import TextContentBlock
from openai.types.beta.threads.text import Text
from openai.types.beta.threads import run_create_params
from openai.types.beta.assistant_tool_param import AssistantToolParam
from openai.types.beta.assistant_tool_choice_option_param import (
    AssistantToolChoiceOptionParam,
)
from openai.types.beta.assistant_response_format_option_param import (
    AssistantResponseFormatOptionParam,
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
TextContentBlock
Text
ToolOutput

StepDetails = Union[MessageCreationStepDetails, ToolCallsStepDetails]


class AssistantCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = Field(None, max_length=512)
    model: str  # This field is required
    instructions: Optional[str] = Field(None, max_length=32768)
    tools: List[AssistantTool] = []
    metadata: Optional[Dict[str, Any]] = None
    response_format: Optional[str] = None
    temperature: Optional[float] = None
    tool_resources: Optional[assistant_create_params.ToolResources] = None
    top_p: Optional[float] = None


class AssistantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = Field(None, max_length=512)
    model: Optional[str] = Field(None, max_length=256)
    instructions: Optional[str] = Field(None, max_length=32768)
    metadata: Optional[Dict[str, Any]] = None
    tools: Optional[List[AssistantTool]] = None  # Simplified for example
    response_format: Optional[str] = None
    temperature: Optional[float] = None
    tool_resources: Optional[assistant_update_params.ToolResources] = None
    top_p: Optional[float] = None


class MessageInput(BaseModel):  # Input for message data
    role: Literal["user", "assistant"]
    content: str
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)
    attachments: Optional[List[Attachment]] = Field(default_factory=list)


class ThreadCreate(BaseModel):
    messages: Optional[List[MessageInput]] = Field(default=[])
    metadata: Optional[Dict[str, str]] = Field(default={})


class ThreadUpdate(BaseModel):
    messages: Optional[List[MessageInput]] = Field(default=[])
    metadata: Optional[Dict[str, str]] = Field(default={})


class MessageUpdate(BaseModel):
    metadata: Optional[Dict[str, str]] = Field(default={})


class RunContent(BaseModel):
    assistant_id: str
    stream: bool = False
    additional_instructions: Optional[str] = None
    additional_messages: Optional[
        Iterable[run_create_params.AdditionalMessage]
    ] = None
    instructions: Optional[str] = None
    max_completion_tokens: Optional[int] = None
    max_prompt_tokens: Optional[int] = None
    metadata: Optional[dict] = None
    model: Optional[str] = None
    response_format: Optional[AssistantResponseFormatOptionParam] = None
    temperature: Optional[float] = None
    tool_choice: Optional[AssistantToolChoiceOptionParam] = None
    tools: Optional[Iterable[AssistantToolParam]] = None
    top_p: Optional[float] = None
    truncation_strategy: Optional[run_create_params.TruncationStrategy] = None
    extra_headers: Optional[dict] = None
    extra_query: Optional[dict] = None
    extra_body: Optional[dict] = None
    timeout: Optional[float] = None


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
    required_action: Optional[RequiredAction] = None


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
        {}, description="Metadata for additional structured information."
    )


class CreateVectorStoreFileBatchRequest(BaseModel):
    file_ids: List[str] = Field(
        ..., min_items=1, max_items=500, example=["file-abc123", "file-abc456"]
    )


class SubmitToolOutputsRunRequest(BaseModel):
    tool_outputs: List[ToolOutput]
    stream: Optional[bool] = None
