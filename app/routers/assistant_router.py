from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from utils.tranformers import db_to_pydantic_assistant

from lib.db.database import get_db
from sqlalchemy.orm import Session
from lib.db import crud, schemas

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
    return db_to_pydantic_assistant(db_assistant)


@router.get(
    "/assistants", response_model=schemas.SyncCursorPage[schemas.Assistant]
)
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

    assistants = [
        db_to_pydantic_assistant(assistant) for assistant in db_assistants
    ]
    paginated_assistants = schemas.SyncCursorPage(data=assistants)

    return paginated_assistants


@router.get("/assistants/{assistant_id}", response_model=schemas.Assistant)
def get_assistant(assistant_id: str, db: Session = Depends(get_db)):
    """
    Retrieves an assistant by its unique ID.

    - **assistant_id**: UUID of the assistant to retrieve.
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
    """
    Updates specified fields of an existing assistant.

    - **assistant_id**: UUID of the assistant to update.
    - **assistant_update**: JSON body containing fields to update on the assistant.
        - `name`: Optional. New name of the assistant (max length: 256).
        - `description`: Optional. New description of the assistant (max length: 512).
        - `model`: Optional. Model ID to use for the assistant (max length: 256).
        - `instructions`: Optional. System instructions for the assistant (max length: 32768).
        - `tools`: Optional. List of tools enabled on the assistant.
        - `metadata`: Optional. Metadata key-value pairs attached to the assistant.
        - `file_ids`: Optional. List of file IDs attached to the assistant.
    """  # noqa
    # Update the assistant with new values
    updated_assistant = crud.update_assistant(
        db=db,
        assistant_id=assistant_id,
        assistant_update=assistant_update.model_dump(exclude_none=True),
    )

    if updated_assistant is None:
        raise HTTPException(status_code=404, detail="Assistant not found")

    return db_to_pydantic_assistant(updated_assistant)


@router.delete(
    "/assistants/{assistant_id}",
    response_model=schemas.AssistantDeleted,
)
def delete_assistant(
    assistant_id: str,
    db: Session = Depends(get_db),
):
    """
    Deletes an assistant by its unique ID.

    - **assistant_id**: UUID of the assistant to delete.
    """
    deletion_success = crud.delete_assistant(db=db, assistant_id=assistant_id)
    if not deletion_success:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return {"id": assistant_id, "deleted": True, "object": "assistant.deleted"}
