import pytest
from openai import OpenAI
from openai.types.beta.thread import Thread

# import os


@pytest.fixture
def openai_client():
    return OpenAI(
        base_url="http://localhost:8000",
        # api_key=os.getenv("OPENAI_API_KEY"),
    )


@pytest.fixture
def assistant_id(openai_client: OpenAI):
    response = openai_client.beta.assistants.create(
        instructions="Speak like shakespeare",
        name="Shakespeare",
        model="gpt-4",
    )
    return response.id


def test_create_thread_without_messages(openai_client: OpenAI):
    thread_metadata = {"example_key": "example_value"}
    response = openai_client.beta.threads.create(metadata=thread_metadata)
    assert isinstance(response, Thread)
    assert response.id is not None
    assert response.object == "thread"
    assert response.created_at is not None
    assert response.metadata == thread_metadata
