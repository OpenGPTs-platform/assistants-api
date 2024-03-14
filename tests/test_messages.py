import pytest
from openai import OpenAI
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


@pytest.mark.dependency()
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


@pytest.mark.dependency(depends=["test_create_message_in_thread"])
def test_get_messages_in_thread(openai_client: OpenAI, thread_id: str):
    # Create some messages in the thread for testing
    message_data_1 = {
        "role": "user",
        "content": "First message",
        "file_ids": [],
        "metadata": {"example_key": "example_value"},
    }
    message_data_2 = {
        "role": "user",
        "content": "Second message",
        "file_ids": [],
    }
    openai_client.beta.threads.messages.create(
        thread_id=thread_id, **message_data_1
    )
    time.sleep(
        1
    )  # TODO: remove this. It adds a gap in btween created_at to ensure a difference in order # noqa
    openai_client.beta.threads.messages.create(
        thread_id=thread_id, **message_data_2
    )

    # Retrieve messages from the thread
    response = openai_client.beta.threads.messages.list(
        thread_id=thread_id, limit=2, order='desc'
    )

    assert len(response.data) == 2
    assert response.data[1].role == message_data_1["role"]
    assert response.data[1].content[0].text.value == message_data_1["content"]
    assert response.data[1].file_ids == message_data_1["file_ids"]
    assert response.data[1].metadata == message_data_1["metadata"]


@pytest.mark.dependency(
    depends=["test_create_message_in_thread", "test_get_messages_in_thread"]
)
def test_create_thread_with_message(openai_client: OpenAI):
    # Create a thread with a message
    message_data = {
        "role": "user",
        "content": "Hello, World!",
        "file_ids": [],
        "metadata": {"example_key": "example_value"},
    }

    create_thread = openai_client.beta.threads.create(messages=[message_data])
    openai_client.beta.threads.messages.retrieve
    assert create_thread.id is not None

    get_messages = openai_client.beta.threads.messages.list(
        thread_id=create_thread.id
    )

    assert len(get_messages.data) == 1
    assert get_messages.data[0].role == message_data["role"]
    assert (
        get_messages.data[0].content[0].text.value == message_data["content"]
    )
    assert get_messages.data[0].file_ids == message_data["file_ids"]
    assert get_messages.data[0].metadata == message_data["metadata"]


@pytest.mark.dependency(
    depends=["test_create_message_in_thread", "test_get_messages_in_thread"]
)
def test_get_specific_message_in_thread(openai_client: OpenAI, thread_id: str):
    # First, create a message in the thread for testing
    message_data = {
        "role": "user",
        "content": "Test message content",
        "file_ids": [],
        "metadata": {"example_key": "example_value"},
    }
    message_response = openai_client.beta.threads.messages.create(
        thread_id=thread_id, **message_data
    )
    message_id = message_response.id

    # Retrieve the specific message from the thread
    retrieved_message = openai_client.beta.threads.messages.retrieve(
        thread_id=thread_id, message_id=message_id
    )

    # Verify the retrieved message details
    assert retrieved_message.id == message_id
    assert retrieved_message.thread_id == thread_id
    assert retrieved_message.role == message_data["role"]
    assert retrieved_message.content[0].text.value == message_data["content"]
    assert retrieved_message.file_ids == message_data["file_ids"]
    assert retrieved_message.metadata == message_data["metadata"]

    # Optionally, cleanup by deleting the message and thread if necessary
