# from enum import Enum
# from openai.types.beta.assistant import (
#     ToolCodeInterpreter,
#     ToolRetrieval,
# )

# # from openai.types.beta.thread import Thread
# from openai.types.beta.threads import ThreadMessage as OpenaiThreadMessage
# from openai.types.beta.threads.runs import RunStep
# from pydantic import BaseModel
# from typing import Dict, List, Union

# Tool = Union[ToolCodeInterpreter, ToolRetrieval]


# class ThreadMessage(OpenaiThreadMessage):
#     pass


# class RunStatus(Enum):
#     QUEUED = "queued"
#     IN_PROGRESS = "in_progress"
#     REQUIRES_ACTION = "requires_action"
#     CANCELLING = "cancelling"
#     CANCELLED = "cancelled"
#     FAILED = "failed"
#     COMPLETED = "completed"
#     EXPIRED = "expired"


# # Thread
# class ThreadMetadata(BaseModel):
#     gpt_id: str = None
#     user_id: str = None
#     title: str = None
#     last_updated: str = None


# class CustomThread(BaseModel):
#     id: str
#     created_at: int
#     metadata: ThreadMetadata


# class UpsertCustomThread(BaseModel):
#     gpt_id: str


# class CreateThreadMessage(BaseModel):
#     content: str


# class CreateThread(BaseModel):
#     title: str


# class MessagesRunStepResponse(BaseModel):
#     messages: List[ThreadMessage]
#     runs_steps: Dict[str, List[RunStep]]
