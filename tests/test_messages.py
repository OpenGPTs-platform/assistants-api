import pytest
from openai import OpenAI
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


def test_create_message_in_thread(openai_client: OpenAI, thread_id: str):
    # Assume create_thread is a helper function that creates a thread and returns its ID
    message_data = {
        "role": "user",
        "content": "Hello, World!",
        "file_ids": [],
        "metadata": {"example_key": "example_value"},
    }

    response = openai_client.beta.threads.messages.create(
        thread_id=thread_id, **message_data
    )

    assert response.id is not None
    assert response.role == message_data["role"]
    assert response.content[0].text.value == message_data["content"]
    assert response.file_ids == message_data["file_ids"]
    assert response.metadata == message_data["metadata"]
