from enum import Enum
from pydantic import BaseModel


class PromptKeys(Enum):
    TRANSITION = "<TRANSITION>"


class WebRetrievalResult(BaseModel):
    url: str
    content: str
    depth: int
