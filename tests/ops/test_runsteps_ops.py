import requests
import pytest
from openai import OpenAI
from openai.types.beta.threads.runs import RunStep
import os
import time

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None


@pytest.fixture
def openai_client():
    return OpenAI(
        base_url="http://localhost:8000",
        api_key=api_key,
    )


@pytest.fixture
def thread_id(openai_client: OpenAI):
    thread_metadata = {"example_key": "example_value"}
    response = openai_client.beta.threads.create(metadata=thread_metadata)
    return response.id


@pytest.fixture
def assistant_id(openai_client: OpenAI):
    response = openai_client.beta.assistants.create(
        instructions="You are an AI designed to provide examples.",
        name="Example Assistant",
        tools=[{"type": "code_interpreter"}],
        model="gpt-3.5-turbo",
    )
    return response.id


@pytest.fixture
def run_id(openai_client: OpenAI, thread_id: str, assistant_id: str):
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    return response.id


@pytest.mark.dependency()
def test_create_run_step(assistant_id: str, thread_id: str, run_id: str):
    create_url = (
        f"http://localhost:8000/ops/threads/{thread_id}/runs/{run_id}/steps"
    )
    step_data = {
        "assistant_id": assistant_id,
        "type": "tool_calls",
        "status": "in_progress",
        "step_details": {"tool_calls": [], "type": "tool_calls"},
    }

    response = requests.post(create_url, json=step_data)

    # Verify the response status code and the returned fields
    assert response.status_code == 200
    created_step = response.json()
    created_step = RunStep(**created_step)
    assert created_step.status == "in_progress"
    assert created_step.type == "tool_calls"
    assert created_step.assistant_id == assistant_id
    assert created_step.thread_id == thread_id
    assert created_step.run_id == run_id
    assert created_step.id is not None

    return created_step.id


@pytest.mark.dependency(depends=["test_create_run_step"])
def test_update_run_step(assistant_id: str, thread_id: str, run_id: str):
    step_id = test_create_run_step(assistant_id, thread_id, run_id)
    update_url = f"http://localhost:8000/ops/threads/{thread_id}/runs/{run_id}/steps/{step_id}"  # noqa
    curr_time = int(time.time())
    update_data = {
        "status": "completed",
        "completed_at": curr_time,
    }

    response = requests.post(update_url, json=update_data)

    # Verify the response status code and the updated fields
    assert response.status_code == 200
    updated_step = response.json()
    updated_step = RunStep(**updated_step)
    assert updated_step.status == "completed"
    assert updated_step.completed_at == curr_time
    assert updated_step.id == step_id
