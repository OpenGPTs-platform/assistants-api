from fastapi import APIRouter, Depends

from db.database import get_db

from sqlalchemy.orm import Session
from db import crud, schemas


router = APIRouter()


@router.post("/assistants", response_model=schemas.Assistant)
def create_assistant(
    assistant: schemas.AssistantCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new assistant.
    - **model**: ID of the model to use.
    - **name**: The name of the assistant.
    - **description**: The description of the assistant.
    - **instructions**: The system instructions that the assistant uses.
    - **tools**: A list of tools enabled on the assistant.
    - **file_ids**: A list of file IDs attached to this assistant.
    - **metadata**: Set of 16 key-value pairs that can be attached to the assistant.
    """
    db_assistant = crud.create_assistant(db=db, assistant=assistant)
    print("db_assistant", db_assistant)
    return db_assistant
