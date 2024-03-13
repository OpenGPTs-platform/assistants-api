from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from lib.db import crud, schemas, database
from utils.tranformers import db_to_pydantic_message

router = APIRouter()


@router.post(
    "/threads/{thread_id}/messages", response_model=schemas.ThreadMessage
)
def create_message_in_thread(
    thread_id: str,
    message: schemas.ThreadMessageCreate,
    db: Session = Depends(database.get_db),
):
    print("INSIDE CREATE MESSAGE IN THREAD", message)
    db_thread = crud.get_thread(db, thread_id=thread_id)
    if db_thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    db_message = crud.create_message(
        db=db, thread_id=thread_id, message=message
    )
    return db_to_pydantic_message(db_message)
