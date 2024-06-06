# api_handler.py
from typing import List, Literal
import uuid
import requests
import os
from data_models import run
from openai.types.beta.threads.message import Message
from openai.types.beta.threads.runs import FileSearchToolCall
from openai.types.beta.threads.runs.web_retrieval_tool_call import (
    WebRetrievalToolCall,
)
from openai.types.beta.threads.runs.function_tool_call import Function
from utils.openai_clients import assistants_client


# TODO: create run script that imports env vars
BASE_URL = os.getenv("ASSISTANTS_API_URL")


def update_run(
    thread_id: str, run_id: str, run_update: run.RunUpdate
) -> run.Run:
    """
    Update the status of a Run.

    Parameters:
    thread_id (str): The ID of the thread.
    run_id (str): The ID of the run.
    new_status (str): The new status to set for the run.

    Returns:
    bool: True if the status was successfully updated, False otherwise.
    """
    update_url = f"{BASE_URL}/ops/threads/{thread_id}/runs/{run_id}"
    update_data = run_update.model_dump(exclude_none=True)

    response = requests.post(update_url, json=update_data)

    if response.status_code == 200:
        return run.Run(**response.json())
    else:
        return None


def create_message(
    thread_id: str, content: str, role: Literal["user", "assistant"]
) -> Message:
    # Create a thread with a message
    message = assistants_client.beta.threads.messages.create(
        thread_id=thread_id, content=content, role=role
    )
    assert message.thread_id == thread_id

    return message


def create_message_runstep(
    thread_id: str, run_id: str, assistant_id: str, content: str
) -> run.RunStep:
    message = create_message(thread_id, content, role="assistant")
    # Prepare run step details
    run_step_details = {
        "assistant_id": assistant_id,
        "step_details": {
            "type": "message_creation",
            "message_creation": {"message_id": message.id},
        },
        "type": "message_creation",
        "status": "completed",
    }
    run_step_details = run.RunStepCreate(**run_step_details).model_dump(
        exclude_none=True
    )

    # Post request to create a run step
    response = requests.post(
        f"{BASE_URL}/ops/threads/{thread_id}/runs/{run_id}/steps",
        json=run_step_details,
    )
    if response.status_code != 200:
        raise Exception(f"Failed to create run step: {response.text}")

    return run.RunStep(**response.json())


def create_retrieval_runstep(
    thread_id: str, run_id: str, assistant_id: str, documents: List[str]
) -> dict:
    # Assuming the `ToolCall` is properly defined elsewhere to include `RetrievalToolCall`. # noqa
    tool_call = FileSearchToolCall(
        id="unique_tool_call_id",  # This should be a unique identifier.
        file_search={"documents": documents},
        type="file_search",
    )

    # Prepare run step details with the tool call
    run_step_details = {
        "assistant_id": assistant_id,
        "step_details": {
            "type": "tool_calls",
            "tool_calls": [
                tool_call.model_dump()
            ],  # Serialize `ToolCall` to a dict
        },
        "type": "tool_calls",
        "status": "completed",
    }

    # This model dumping part would be dependent on how you're handling Pydantic models, showing a conceptual example: # noqa
    run_step_details = run.RunStepCreate(**run_step_details).model_dump(
        exclude_none=True
    )

    # Post request to create a run step
    response = requests.post(
        f"{BASE_URL}/ops/threads/{thread_id}/runs/{run_id}/steps",
        json=run_step_details,
    )
    if response.status_code != 200:
        raise Exception(f"Failed to create run step: {response.text}")

    return run.RunStep(**response.json())


def create_web_retrieval_runstep(
    thread_id: str,
    run_id: str,
    assistant_id: str,
    retreived_content: List[str],
    site: str,
) -> dict:
    # Assuming the `ToolCall` is properly defined elsewhere to include `RetrievalToolCall`. # noqa
    tool_call = WebRetrievalToolCall(
        id="unique_tool_call_id",  # TODO: This should be a unique identifier.
        retrieval=retreived_content,
        site=site,
        type="web_retrieval",
    )

    # Prepare run step details with the tool call
    run_step_details = {
        "assistant_id": assistant_id,
        "step_details": {
            "type": "tool_calls",
            "tool_calls": [
                tool_call.model_dump()
            ],  # Serialize `ToolCall` to a dict
        },
        "type": "tool_calls",
        "status": "completed",
    }

    # This model dumping part would be dependent on how you're handling Pydantic models, showing a conceptual example: # noqa
    run_step_details = run.RunStepCreate(**run_step_details).model_dump(
        exclude_none=True
    )

    # Post request to create a run step
    response = requests.post(
        f"{BASE_URL}/ops/threads/{thread_id}/runs/{run_id}/steps",
        json=run_step_details,
    )
    if response.status_code != 200:
        raise Exception(f"Failed to create run step: {response.text}")

    return run.RunStep(**response.json())


def create_function_runstep(
    thread_id: str,
    run_id: str,
    assistant_id: str,
    function: Function,
) -> dict:
    # Prepare run step details with the tool call
    run_step_details = {
        "assistant_id": assistant_id,
        "step_details": {
            "type": "tool_calls",
            "tool_calls": [
                {
                    "id": "call_"
                    + str(uuid.uuid4()),  # This should be a unique identifier.
                    "function": function,
                    "type": "function",
                }
            ],  # Serialize `ToolCall` to a dict
        },
        "type": "tool_calls",
        "status": "in_progress",
    }

    # This model dumping part would be dependent on how you're handling Pydantic models, showing a conceptual example: # noqa
    run_step_details = run.RunStepCreate(**run_step_details).model_dump(
        exclude_none=True
    )

    # Post request to create a run step
    response = requests.post(
        f"{BASE_URL}/ops/threads/{thread_id}/runs/{run_id}/steps",
        json=run_step_details,
    )
    if response.status_code != 200:
        raise Exception(f"Failed to create run step: {response.text}")

    return run.RunStep(**response.json())
