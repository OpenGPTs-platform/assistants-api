from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any, Union
from openai.types.beta.threads.runs import (
    RunStep,
    MessageCreationStepDetails,
    ToolCallsStepDetails,
)

RunStep

StepDetails = Union[MessageCreationStepDetails, ToolCallsStepDetails]


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
