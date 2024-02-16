from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException
from utils.parsers import get_user_id
from db.database import get_db
from sqlalchemy.orm import Session
from db import crud, schemas
from models.thread import (
    CreateThread,
    MessagesRunStepResponse,
    CustomThread,
    CreateThreadMessage,
    ThreadMessage,
    ThreadMetadata,
)
from datetime import datetime
import time
from utils.api import get_run_steps, openai_client
from openai.types.beta.threads.runs import RunStep
import json


router = APIRouter()


@router.post("/gpt/{gpt_id}/thread", response_model=CustomThread)
def create_thread(
    request: CreateThread,
    gpt_id: str,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a thread.

    Args:
    - gpt_id (str): The ID of the GPT.
    - request (CreateThread): More thread details.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - CustomThread: The created thread.
    """
    thread_metadata: ThreadMetadata = {
        "title": request.title,
        "gpt_id": gpt_id,
        "user_id": user_id,
        "last_updated": int(datetime.now().timestamp()).__str__(),
    }
    thread = openai_client.beta.threads.create(metadata=thread_metadata)

    user_gpt_thread = schemas.UserGptThread(
        user_id=user_id,
        gpt_id=gpt_id,
        thread_id=thread.id,
    )
    crud.create_thread(db=db, user_gpt_thread=user_gpt_thread)
    return CustomThread(**thread.model_dump())


@router.get("/thread", response_model=List[CustomThread])
def get_threads(
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Get user threads.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - List[CustomThread]: The list of threads.
    """
    db_threads = crud.get_user_threads(db, user_id)
    threads = []
    for db_thread in db_threads:
        thread = openai_client.beta.threads.retrieve(db_thread.thread_id)
        threads.append(thread)
    return threads


@router.delete("/thread")
def delete_all_treads(db: Session = Depends(get_db)):
    crud.delete_all_threads(db)


@router.post(
    "/gpt/{gpt_id}/thread/{thread_id}/messages",
    response_model=List[ThreadMessage],
)
def create_thread_message(
    gpt_id: str,
    thread_id: str,
    request: CreateThreadMessage,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a message in a thread.

    Args:
    - request (CreateThreadMessage): The message to create.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - List[ThreadMessage]: The message history including the
      assistant response.
    """
    try:
        user_message = openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=request.content,
        )

        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=gpt_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="GPT run failed. With status: " + e.__str__(),
        )

    max_wait_iterations = 30  # (max_wait_iterations / 2) = seconds to wait
    i = 0
    while i < max_wait_iterations:
        i += 1
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id,
        )

        print("RUN: ", json.dumps(run.model_dump(), indent=2))

        if run.status == "completed":
            break
        elif not (run.status == "in_progress" or run.status == "queued"):
            raise HTTPException(
                status_code=500,
                detail="GPT run failed. With status: " + run.status,
            )

        time.sleep(0.5)
    else:
        raise HTTPException(
            status_code=500,
            detail="GPT timeout. With status: " + run.status,
        )
    print("RUN: ", run)

    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_id,
    )
    messages_list: List[ThreadMessage] = []
    for message in messages:
        print("MESSAGE: ", json.dumps(message.model_dump(), indent=2))
        messages_list.append(message)
        if message.id == user_message.id:
            break

    return messages_list


@router.get(
    "/gpt/{gpt_id}/thread/{thread_id}/messages",
    response_model=List[ThreadMessage],
)
def get_thread_messages(
    gpt_id: str,
    thread_id: str,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Get all messages in a thread.

    Args:
    - thread_id (str): The ID of the thread.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - List[ThreadMessage]: All of the messages in a the thread.
    """
    if not crud.get_user_gpt_thread(db, user_id, gpt_id, thread_id):
        raise HTTPException(
            status_code=404,
            detail="User does not have access to this thread.",
        )

    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_id,
    )
    messages_list = [message for message in messages]
    return messages_list


# TODO: takes a while to retrieve, transform this to a stream
@router.get(
    "/gpt/{gpt_id}/thread/{thread_id}/run",
    response_model=MessagesRunStepResponse,
)
def get_thread_runs(
    gpt_id: str,
    thread_id: str,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Get all run steps in a thread.

    Args:
    - gp_id (str): The ID of the GPT.
    - thread_id (str): The ID of the thread.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - RunStepsResponse: The run steps in the thread and a hash map of
      messages.
    """
    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_id,
    )
    message_exchange: List[ThreadMessage] = []
    runs_steps: Dict[str, List[RunStep]] = {}

    for message in messages:
        if message.run_id and runs_steps.get(message.run_id) is None:
            run_steps = get_run_steps(openai_client, thread_id, message.run_id)
            runs_steps[message.run_id] = run_steps
        message_exchange.append(message)

    return MessagesRunStepResponse(
        messages=[message.model_dump() for message in message_exchange],
        runs_steps=runs_steps,
    )


def check_step_status(step):
    if not (
        step.status == "in_progress"
        or step.status == "queued"
        or step.status == "completed"
    ):
        raise HTTPException(
            status_code=500,
            detail="GPT run failed. With status: " + step.status,
        )


@router.post(
    "/gpt/{gpt_id}/thread/{thread_id}/run",
    response_model=MessagesRunStepResponse,
)
def create_thread_run(
    gpt_id: str,
    thread_id: str,
    request: CreateThreadMessage,
    user_id: str = Depends(get_user_id),
    db: Session = Depends(get_db),
):
    """
    Create a message in a thread.

    Args:
    - request (CreateThreadMessage): The message to create.

    Headers:
    - auth (str): Bearer <JWT_TOKEN>

    Returns:
    - RunStepsResponse: The run steps in the run and a hash map of
      messages.
    """
    message_exchange: List[ThreadMessage] = []
    runs_steps: Dict[str, List[RunStep]] = {}
    user_message = openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=request.content,
    )
    run = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=gpt_id,
    )

    max_wait_iterations = 20  # (max_wait_iterations / 2) = seconds to wait
    i = 0
    while i < max_wait_iterations:
        i += 1

        run_steps_response = get_run_steps(
            openai_client, thread_id, run.id, check_step_status
        )
        runs_steps[run.id] = run_steps_response

        json_run_steps = [step.model_dump() for step in run_steps_response]
        if len(json_run_steps) and all(
            [step["status"] == "completed" for step in json_run_steps]
        ):
            for step in run_steps_response:
                if step.type == "message_creation":
                    message_id = step.step_details.message_creation.message_id
                    message = openai_client.beta.threads.messages.retrieve(
                        thread_id=thread_id,
                        message_id=message_id,
                    )
                    message_exchange.append(message.model_dump())
            message_exchange.append(user_message.model_dump())
            break

        time.sleep(0.5)
    else:
        raise HTTPException(
            status_code=500,
            detail="GPT run timed out.",
        )

    return MessagesRunStepResponse(
        messages=message_exchange,
        runs_steps=runs_steps,
    )
