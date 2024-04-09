import requests
import pytest
from openai import OpenAI
from openai.types.beta.threads import Run
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
def test_update_run(thread_id: str, run_id: str):
    # Assuming you have a way to get a run_id, perhaps from the test_create_run test
    curr_time = int(time.time())
    update_url = f"http://localhost:8000/ops/threads/{thread_id}/runs/{run_id}"
    update_data = {
        "status": "completed",
        "completed_at": curr_time,
    }

    response = requests.post(update_url, json=update_data)

    # Verify the response status code and the updated fields
    assert response.status_code == 200
    updated_run = response.json()
    updated_run = Run(**updated_run)
    assert updated_run.status == "completed"
    assert updated_run.completed_at == curr_time
    assert updated_run.id == run_id

    # You might want to fetch the updated run again using a GET request to double-check
