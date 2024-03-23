# In your FastAPI router file
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from lib.db import (
    crud,
    schemas,
    database,
)  # Import your CRUD handlers, schemas, and models
from lib.mb.broker import RabbitMQBroker, get_broker
from utils.tranformers import db_to_pydantic_run

router = APIRouter()


@router.post("/threads/{thread_id}/runs", response_model=schemas.Run)
def create_run(
    thread_id: str = Path(..., title="The ID of the thread to run"),
    run: schemas.RunContent = Body(..., title="The run content"),
    db: Session = Depends(database.get_db),
    broker: RabbitMQBroker = Depends(get_broker),
):
    """
    Create a new run within a specified thread.

    This endpoint creates a new run associated with a given thread, using the provided run content.
    It ensures that the specified thread exists and validates the run content against the associated assistant.
    If the creation is successful, the new run's ID is published to a RabbitMQ queue for further processing.

    Parameters:
    - thread_id (str): The ID of the thread in which the run is to be created.
    - run (schemas.RunContent): The content of the run, including any specific instructions, model ID, and tools.

    Returns:
    - The newly created run as a Pydantic model, conforming to schemas.Run.

    Raises:
    - HTTPException: If the run creation fails, an HTTP 500 error is returned with a failure detail.
    """  # noqa
    db_run = crud.create_run(db=db, thread_id=thread_id, run=run)
    if db_run is None:
        raise HTTPException(status_code=500, detail="Run creation failed")

    # After successful creation, publish the run ID to the RabbitMQ queue
    broker.publish("runs_queue", str(db_run.id))
    broker.close_connection()

    return db_to_pydantic_run(db_run)


@router.get("/threads/{thread_id}/runs/{run_id}", response_model=schemas.Run)
def read_run(
    thread_id: str, run_id: str, db: Session = Depends(database.get_db)
):
    db_run = crud.get_run(db, run_id=run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return db_to_pydantic_run(db_run)
