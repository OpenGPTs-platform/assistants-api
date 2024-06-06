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
import json

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
    db_run = crud.create_run(db=db, thread_id=thread_id, run_params=run)
    if db_run is None:
        raise HTTPException(status_code=500, detail="Run creation failed")

    # After successful creation, publish the run ID to the RabbitMQ queue
    data = {"thread_id": thread_id, "run_id": str(db_run.id)}
    message = json.dumps(data)
    broker.publish("runs_queue", message)
    broker.close_connection()

    return db_to_pydantic_run(db_run)


@router.get("/threads/{thread_id}/runs/{run_id}", response_model=schemas.Run)
def read_run(
    thread_id: str, run_id: str, db: Session = Depends(database.get_db)
):
    db_run = crud.get_run(db, thread_id=thread_id, run_id=run_id)
    if db_run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return db_to_pydantic_run(db_run)


@router.post(
    "/threads/{thread_id}/runs/{run_id}/cancel", response_model=schemas.Run
)
def cancel_run(
    thread_id: str, run_id: str, db: Session = Depends(database.get_db)
):
    run = crud.cancel_run(db, thread_id=thread_id, run_id=run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return db_to_pydantic_run(run)


@router.post(
    "/threads/{thread_id}/runs/{run_id}/submit_tool_outputs",
    response_model=schemas.Run,
)
def submit_tool_outputs(
    *,
    thread_id: str = Path(
        ..., description="The ID of the thread to which this run belongs."
    ),
    run_id: str = Path(
        ...,
        description="The ID of the run that requires the tool output submission.",
    ),
    body: schemas.SubmitToolOutputsRunRequest = Body(
        ..., description="Request body containing tool outputs."
    ),
    db: Session = Depends(database.get_db),
    broker: RabbitMQBroker = Depends(get_broker),
):
    # Logic to handle the submission of tool outputs
    # This will involve updating the database and performing necessary actions
    try:
        db_run = crud.submit_tool_outputs(
            db=db,
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=body.tool_outputs,
        )
        # After successful creation, publish the run ID to the RabbitMQ queue
        data = {"thread_id": thread_id, "run_id": str(db_run.id)}
        message = json.dumps(data)
        broker.publish("runs_queue", message)
        broker.close_connection()

        return db_to_pydantic_run(db_run)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
