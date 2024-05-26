# In your FastAPI router file
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from lib.db import (
    crud,
    schemas,
    database,
)  # Import your CRUD handlers, schemas, and models
from utils.tranformers import db_to_pydantic_run

router = APIRouter()


@router.post(
    "/ops/threads/{thread_id}/runs/{run_id}", response_model=schemas.Run
)
def update_run(
    thread_id: str = Path(..., title="The ID of the thread"),
    run_id: str = Path(..., title="The ID of the run to update"),
    run_update: schemas.RunUpdate = Body(..., title="The fields to update"),
    db: Session = Depends(database.get_db),
):
    db_run = crud.update_run(
        db,
        thread_id=thread_id,
        run_id=run_id,
        run_update=run_update.model_dump(exclude_none=True),
    )
    if db_run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return db_to_pydantic_run(db_run)
