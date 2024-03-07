from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from lib.db import schemas, database, crud
from utils.tranformers import db_to_pydantic_thread

router = APIRouter()


@router.post("/threads", response_model=schemas.Thread)
def create_thread(
    thread_data: schemas.ThreadCreate, db: Session = Depends(database.get_db)
):
    """
    Create a new thread.
    - **metadata**: Set of 16 key-value pairs that can be attached to the thread.
    """

    database.reset_db()

    db_thread = crud.create_thread(db, thread_data)
    print("db_thread", db_thread.__dict__)

    return db_to_pydantic_thread(db_thread)


@router.get("/threads/{thread_id}", response_model=schemas.Thread)
def get_thread(thread_id: str, db: Session = Depends(database.get_db)):
    """
    Retrieve a specific thread by its ID.
    - **thread_id**: The ID of the thread to retrieve.
    """
    db_thread = crud.get_thread(db, thread_id=thread_id)
    if db_thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    return db_to_pydantic_thread(db_thread)


@router.post("/threads/{thread_id}", response_model=schemas.Thread)
def update_thread(
    thread_id: str,
    thread_data: schemas.ThreadUpdate,
    db: Session = Depends(database.get_db),
):
    """
    Update a specific thread by its ID.
    - **thread_id**: The ID of the thread to update.
    - **metadata**: Set of 16 key-value pairs that can be attached to the thread.
    """
    db_thread = crud.update_thread(
        db, thread_id, thread_data.model_dump(exclude_none=True)
    )
    if db_thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    return db_to_pydantic_thread(db_thread)
