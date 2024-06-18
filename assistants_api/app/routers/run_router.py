# In your FastAPI router file
from typing import List, Literal, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Path
from openai import BaseModel
from sqlalchemy.orm import Session
from lib.db import (
    crud,
    schemas,
    database,
)  # Import your CRUD handlers, schemas, and models
from lib.mb.broker import RabbitMQBroker, get_broker
from utils.tranformers import db_to_pydantic_run
import json
from fastapi.responses import StreamingResponse
import asyncio


router = APIRouter()


# @router.post("/threads/{thread_id}/runs", response_model=schemas.Run)
@router.post("/threads/{thread_id}/runs")
async def create_run(
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

    data = {"thread_id": thread_id, "run_id": str(db_run.id)}
    message = json.dumps(data)
    broker.publish("runs_queue", message)
    broker.close_connection()

    if run.stream:
        run_id = str(db_run.id)
        print("Streaming updates: ", run_id)
        return await stream_run_updates(run_id)  # Await the coroutine here

    return db_to_pydantic_run(db_run)


class TextDelta(BaseModel):
    annotations: Optional[
        List[str]
    ] = None  # Replace str with actual type if available
    value: Optional[str] = None


class TextDeltaBlock(BaseModel):
    index: int
    """The index of the content part in the message."""

    type: Literal["text"]
    """Always `text`."""

    text: Optional[TextDelta] = None


class MessageDelta(BaseModel):
    content: Optional[List[TextDeltaBlock]] = None
    """The content of the message in array of text and/or images."""

    role: Optional[Literal["user", "assistant"]] = None
    """The entity that produced the message. One of `user` or `assistant`."""


class MessageDeltaEvent(BaseModel):
    id: str
    """The identifier of the message, which can be referenced in API endpoints."""

    delta: MessageDelta
    """The delta containing the fields that have changed on the Message."""

    object: Literal["thread.message.delta"]
    """The object type, which is always `thread.message.delta`."""


class ToolCallDeltaObject(BaseModel):
    type: Literal["tool_calls"]
    """Always `tool_calls`."""

    tool_calls: Optional[List[dict]] = None
    """An array of tool calls the run step was involved in.

    These can be associated with one of three types of tools: `code_interpreter`,
    `file_search`, or `function`.
    """


class RunStepDelta(BaseModel):
    step_details: Optional[ToolCallDeltaObject] = None
    """The details of the run step."""


class RunStepDeltaEvent(BaseModel):
    id: str
    """The identifier of the run step, which can be referenced in API endpoints."""

    delta: RunStepDelta
    """The delta containing the fields that have changed on the run step."""

    object: Literal["thread.run.step.delta"]
    """The object type, which is always `thread.run.step.delta`."""


class ThreadRunStepDelta(BaseModel):
    data: RunStepDeltaEvent
    """Represents a run step delta i.e.

    any changed fields on a run step during streaming.
    """

    event: Literal["thread.run.step.delta"]


class ThreadMessageDelta(BaseModel):
    data: MessageDeltaEvent
    event: Literal["thread.message.delta"]


class InitialMessageEvent(BaseModel):
    id: str
    content: List[TextDeltaBlock]
    role: Literal["assistant"]
    object: Literal["thread.message"]
    # Include any additional fields necessary for the initial message


async def stream_run_updates(run_id: str):
    async def event_generator():
        try:
            run_step = {
                "data": {
                    "id": f"step_{run_id}",
                    "run_id": run_id,
                    "status": "in_progress",
                    "step_details": {"type": "tool_calls", "tool_calls": []},
                    "thread_id": "thread_12345",
                    "type": "tool_calls",
                    "object": "thread.run.step",
                },
                "event": "thread.run.step.created",
            }
            yield f"event: {run_step['event']}\ndata: {json.dumps(run_step['data'])}\n\n"  # noqa
            await asyncio.sleep(1)

            # Emit run step deltas
            for i in range(3):  # Simulate 3 deltas for the run step
                run_step_delta = ThreadRunStepDelta(
                    data=RunStepDeltaEvent(
                        id=f"step_{run_id}",
                        delta=RunStepDelta(
                            step_details=ToolCallDeltaObject(
                                type="tool_calls",
                                tool_calls=[
                                    {
                                        "index": 0,
                                        "type": "code_interpreter",
                                        "id": "call_yJMgNvtnIfzt78hCGBVA5gIb",
                                        "code_interpreter": {
                                            "input": str(i),
                                            "outputs": [],
                                        },
                                    }
                                ],
                            )
                        ),
                        object="thread.run.step.delta",
                    ),
                    event="thread.run.step.delta",
                )
                print("SENDING STEP DELTA")
                yield f"event: {run_step_delta.event}\ndata: {run_step_delta.data.json()}\n\n"  # noqa
                await asyncio.sleep(1)

            initial_message = InitialMessageEvent(
                id=f"message_{run_id}",
                content=[],
                role="assistant",
                object="thread.message",
            )
            yield f"event: thread.message.created\ndata: {initial_message.json()}\n\n"  # noqa
            await asyncio.sleep(1)

            # initial_message = InitialMessageEvent(
            #     id=f"message_{run_id}",
            #     content=[],
            #     role="assistant",
            #     object="thread.message",
            # )
            # yield f"event: thread.message.in_progress\ndata: {initial_message.json()}\n\n" # noqa
            # await asyncio.sleep(1)

            for i in range(3):  # Simulate 5 updates
                message_delta = ThreadMessageDelta(
                    data=MessageDeltaEvent(
                        id=f"message_{run_id}",
                        delta=MessageDelta(
                            content=[
                                TextDeltaBlock(
                                    **{
                                        "index": 0,
                                        "type": "text",
                                        "text": {
                                            "annotations": None,
                                            "value": f"{i}",
                                        },
                                    }
                                )
                            ],
                            role=None,
                        ),
                        object="thread.message.delta",
                    ),
                    event="thread.message.delta",
                )
                yield f"event: {message_delta.event}\ndata: {message_delta.data.json()}\n\n"  # noqa
                await asyncio.sleep(1)  # Simulate delay between updates

        except asyncio.CancelledError:
            print("Client disconnected")
        except Exception as e:
            print(f"Error in streaming: {e}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
