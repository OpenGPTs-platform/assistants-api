# In your FastAPI router file
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from lib.db import (
    crud,
    schemas,
    database,
)  # Import your CRUD handlers, schemas, and models
from utils.tranformers import db_to_pydantic_runstep

router = APIRouter()


# TODO: improve test to actually inspect the run steps
@router.post(
    "/ops/threads/{thread_id}/runs/{run_id}/steps",
    response_model=schemas.RunStep,
)
def create_run_step(
    thread_id: str = Path(..., title="The ID of the thread"),
    run_id: str = Path(..., title="The ID of the run"),
    run_step: schemas.RunStepCreate = Body(..., title="Run step details"),
    db: Session = Depends(database.get_db),
):
    # Logic to create a run step
    db_run_step = crud.create_run_step(
        db=db, thread_id=thread_id, run_id=run_id, run_step=run_step
    )
    if db_run_step is None:
        raise HTTPException(status_code=500, detail="Run step creation failed")
    return db_to_pydantic_runstep(db_run_step)


@router.post(
    "/ops/threads/{thread_id}/runs/{run_id}/steps/{step_id}",
    response_model=schemas.RunStep,
)
def update_run_step(
    thread_id: str = Path(..., title="The ID of the thread"),
    run_id: str = Path(..., title="The ID of the run"),
    step_id: str = Path(..., title="The ID of the run step to update"),
    run_step_update: schemas.RunStepUpdate = Body(
        ..., title="Fields to update"
    ),
    db: Session = Depends(database.get_db),
):
    db_run_step = crud.update_run_step(
        db=db,
        thread_id=thread_id,
        run_id=run_id,
        step_id=step_id,
        run_step_update=run_step_update.model_dump(exclude_none=True),
    )
    if db_run_step is None:
        raise HTTPException(status_code=404, detail="Run step not found")
    return db_to_pydantic_runstep(db_run_step)
