from pydantic import BaseModel
from typing import Literal, Optional, List, Any, Union
from enum import Enum
from openai.types.beta.threads.run import Run
from openai.types.beta.threads.runs import (
    RunStep,
    MessageCreationStepDetails,
    ToolCallsStepDetails,
)

Run
RunStep


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


class RunStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    REQUIRES_ACTION = "requires_action"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"
    EXPIRED = "expired"


StepDetails = Union[MessageCreationStepDetails, ToolCallsStepDetails]


class RunStepCreate(BaseModel):
    # Define the fields required for creating a RunStep
    assistant_id: str
    step_details: Any
    type: Literal["message_creation", "tool_calls"]
    status: Literal[
        "in_progress", "cancelled", "failed", "completed", "expired"
    ]
    step_details: StepDetails
