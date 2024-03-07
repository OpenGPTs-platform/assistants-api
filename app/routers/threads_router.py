from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from lib.db import schemas, database, crud

router = APIRouter()


@router.post("/threads", response_model=schemas.Thread)
def create_thread(
    thread_data: schemas.ThreadCreate, db: Session = Depends(database.get_db)
):
    """
    Create a new thread.
    - **metadata**: Set of 16 key-value pairs that can be attached to the thread.
    """

    db_thread = crud.create_thread(db, thread_data)

    return schemas.Thread(
        id=db_thread.id,
        created_at=db_thread.created_at,
        metadata=db_thread.metadata,
        object="thread",
    )
