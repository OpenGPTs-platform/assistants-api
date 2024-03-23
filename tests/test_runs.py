import pytest
from openai import OpenAI
from openai.types.beta.threads import Run
import os

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


@pytest.mark.dependency()
def test_create_run(openai_client: OpenAI, thread_id: str, assistant_id: str):
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    assert isinstance(response, Run)
    assert response.id is not None
    assert response.thread_id == thread_id
    assert response.assistant_id == assistant_id
    # Additional assertions can be added based on the expected response


@pytest.mark.dependency(depends=["test_create_run"])
def test_create_run_with_modified_instruction(
    openai_client: OpenAI, thread_id: str, assistant_id: str
):
    instructions = "You are a human."
    additional_instructions = "Your job is to be useless."
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions=instructions,
        additional_instructions=additional_instructions,
    )

    assert isinstance(response, Run)
    assert response.id is not None
    assert response.thread_id == thread_id
    assert response.assistant_id == assistant_id
    assert (
        response.instructions == instructions + " " + additional_instructions
    )
    # Additional assertions can be added based on the expected response


@pytest.fixture
def run_id_and_thread_id(
    openai_client: OpenAI, thread_id: str, assistant_id: str
):
    response = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )
    return (response.id, thread_id)


@pytest.mark.dependency(depends=["test_create_run"])
def test_get_run(openai_client: OpenAI, run_id_and_thread_id: tuple):
    response = openai_client.beta.threads.runs.retrieve(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    openai_client.beta.threads.runs.cancel

    # Validate the response structure and data (simplified example)
    assert response.id == run_id_and_thread_id[0]
    assert response.object == "thread.run"
    assert response.thread_id == run_id_and_thread_id[1]
    assert response.assistant_id is not None
    assert response.status in [
        "queued",
        "in_progress",
        "requires_action",
        "cancelling",
        "cancelled",
        "failed",
        "completed",
        "expired",
    ]


@pytest.mark.dependency(depends=["test_create_run", "test_get_run"])
def test_cancel_run(openai_client: OpenAI, run_id_and_thread_id: tuple):
    progress_run_response = openai_client.beta.threads.runs.retrieve(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    assert progress_run_response.status in [
        "queued",
        "in_progress",
        "requires_action",
    ]

    # Test Execution
    response = openai_client.beta.threads.runs.cancel(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    # Assertions
    assert response.id == run_id_and_thread_id[0]
    assert response.status in ["cancelling", "cancelled"]

    post_cancel_run_response = openai_client.beta.threads.runs.retrieve(
        run_id=run_id_and_thread_id[0], thread_id=run_id_and_thread_id[1]
    )

    assert post_cancel_run_response.id == run_id_and_thread_id[0]
    assert post_cancel_run_response.status in ["cancelling", "cancelled"]
