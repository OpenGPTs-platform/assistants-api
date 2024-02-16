from enum import Enum
from openai.types.beta.assistant import (
    ToolCodeInterpreter,
    ToolRetrieval,
)
from pydantic import BaseModel
from typing import Optional, List, Union

Tool = Union[ToolCodeInterpreter, ToolRetrieval]


class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class Model(str, Enum):
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4_TURBO_PREVIEW = "gpt-4-turbo-preview"


class IsStaging(str, Enum):
    TRUE = "true"


# TODO: align GPT with assistant
class GptMetadata(BaseModel):
    user_name: str
    # TODO: add GPT image
    visibility: Visibility
    gpt_image: str
    is_staging: Optional[IsStaging]
    ref: Optional[str]


class Gpt(BaseModel):
    id: str
    name: str
    model: Model
    metadata: GptMetadata
    description: Optional[str]
    instructions: Optional[str]
    file_ids: list[str]
    tools: List[Tool]


class GptMetadataMain(BaseModel):
    user_name: str
    visibility: Visibility
    gpt_image: str


class GptMain(Gpt):
    metadata: GptMetadataMain


class GptMetadataStaging(BaseModel):
    user_name: str
    visibility: Visibility
    gpt_image: str
    is_staging: IsStaging
    ref: str


class GptStaging(Gpt):
    metadata: GptMetadataStaging


# same as gpt but without id
class UpsertGpt(BaseModel):
    name: str
    model: Model
    metadata: GptMetadataMain
    description: Optional[str]
    instructions: Optional[str]
    file_ids: list[str]
    tools: List[Tool]
