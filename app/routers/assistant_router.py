from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from utils.tranformers import db_to_pydantic_assistant

from db.database import get_db
from sqlalchemy.orm import Session
from db import crud, schemas
from openai.pagination import SyncCursorPage

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
    return db_assistant


@router.get("/assistants", response_model=SyncCursorPage[schemas.Assistant])
def list_assistants(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, le=100),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    after: Optional[str] = None,
    before: Optional[str] = None,
):
    """
    List assistants with optional pagination and ordering.
    - **limit**: Maximum number of results to return.
    - **order**: Sort order based on the creation time ('asc' or 'desc').
    - **after**: ID to start the list from (for pagination).
    - **before**: ID to list up to (for pagination).
    """
    db_assistants = crud.get_assistants(
        db=db, limit=limit, order=order, after=after, before=before
    )
    if not db_assistants:
        raise HTTPException(status_code=404, detail="Assistants not found")
    assistants = [
        db_to_pydantic_assistant(assistant) for assistant in db_assistants
    ]
    paginated_assistants = SyncCursorPage(data=assistants)

    return paginated_assistants


@router.get("/assistants/{assistant_id}", response_model=schemas.Assistant)
def get_assistant(assistant_id: str, db: Session = Depends(get_db)):
    """
    Retrieves an assistant by ID.
    """
    db_assistant = crud.get_assistant_by_id(db=db, assistant_id=assistant_id)
    if db_assistant is None:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return db_to_pydantic_assistant(db_assistant)


@router.post("/assistants/{assistant_id}", response_model=schemas.Assistant)
def update_assistant(
    assistant_id: str,
    assistant_update: schemas.AssistantUpdate,
    db: Session = Depends(get_db),
):
    # Retrieve the existing assistant
    db_assistant = crud.get_assistant_by_id(db=db, assistant_id=assistant_id)
    if db_assistant is None:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # Update the assistant with new values
    updated_assistant = crud.update_assistant(
        db=db,
        assistant_id=assistant_id,
        assistant_update=assistant_update.model_dump(exclude_none=True),
    )

    return db_to_pydantic_assistant(updated_assistant)
