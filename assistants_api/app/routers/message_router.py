from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from typing import Optional
from sqlalchemy.orm import Session
from lib.db import crud, schemas, database
from utils.tranformers import db_to_pydantic_message

router = APIRouter()


@router.post("/threads/{thread_id}/messages", response_model=schemas.Message)
def create_message_in_thread(
    thread_id: str,
    message_inp: schemas.MessageInput,
    db: Session = Depends(database.get_db),
):
    db_thread = crud.get_thread(db, thread_id=thread_id)
    if db_thread is None:
        raise HTTPException(status_code=404, detail="No thread found")

    db_message = crud.create_message(
        db=db, thread_id=thread_id, message_inp=message_inp
    )
    return db_to_pydantic_message(db_message)


@router.get(
    "/threads/{thread_id}/messages",
    response_model=schemas.SyncCursorPage[schemas.Message],
)
def get_messages_in_thread(
    thread_id: str,
    db: Session = Depends(database.get_db),
    limit: int = Query(default=20, le=100),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    after: Optional[str] = None,
    before: Optional[str] = None,
):
    """
    List messages in a thread with optional pagination and ordering.
    - **limit**: Maximum number of results to return.
    - **order**: Sort order based on the creation time ('asc' or 'desc').
    - **after**: ID to start the list from (for pagination).
    - **before**: ID to list up to (for pagination).
    """
    db_messages = crud.get_messages(
        db=db,
        thread_id=thread_id,
        limit=limit,
        order=order,
        after=after,
        before=before,
    )

    messages = [db_to_pydantic_message(message) for message in db_messages]
    paginated_messages = schemas.SyncCursorPage(data=messages)

    return paginated_messages


@router.get(
    "/threads/{thread_id}/messages/{message_id}",
    response_model=schemas.Message,
)
def get_message(
    thread_id: str,
    message_id: str,
    db: Session = Depends(database.get_db),
):
    """
    Retrieve a specific message from a thread.
    - **thread_id**: The ID of the thread.
    - **message_id**: The ID of the message to retrieve.
    """
    message_db = crud.get_message_by_id(
        db, thread_id=thread_id, message_id=message_id
    )
    if not message_db:
        raise HTTPException(status_code=404, detail="Message not found")
    return db_to_pydantic_message(message_db)


@router.post(
    "/threads/{thread_id}/messages/{message_id}",
    response_model=schemas.Message,
)
def modify_message(
    thread_id: str = Path(
        ..., description="The ID of the thread to which this message belongs."
    ),
    message_id: str = Path(
        ..., description="The ID of the message to modify."
    ),
    update_data: schemas.MessageUpdate = Body(...),
    db: Session = Depends(database.get_db),
):
    """
    Modifies a message.
    - **thread_id**: The ID of the thread.
    - **message_id**: The ID of the message to modify.
    - **update_data**: Data for updating the message.
    """
    db_message = crud.update_message(
        db, thread_id, message_id, update_data.model_dump(exclude_none=True)
    )
    if db_message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return db_to_pydantic_message(db_message)
