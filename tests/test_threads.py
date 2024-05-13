import pytest
from openai import OpenAI
from openai.types.beta.thread import Thread
import os
import time

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None
use_openai = True if os.getenv("USE_OPENAI") else False
base_url = "http://localhost:8000"


@pytest.fixture
def openai_client():
    if use_openai:
        return OpenAI(
            api_key=api_key,
        )
    else:
        return OpenAI(
            base_url=base_url,
        )


@pytest.fixture
def thread_id(openai_client: OpenAI):
    thread_metadata = {"example_key": "example_value"}
    response = openai_client.beta.threads.create(metadata=thread_metadata)
    return response.id


@pytest.mark.dependency()
def test_create_thread_without_messages(openai_client: OpenAI):
    thread_metadata = {"example_key": "example_value"}
    response = openai_client.beta.threads.create(metadata=thread_metadata)
    assert isinstance(response, Thread)
    assert response.id is not None
    assert response.object == "thread"
    assert response.created_at is not None
    assert response.metadata == thread_metadata


@pytest.mark.dependency(depends=["test_create_thread_without_messages"])
def test_get_thread(openai_client: OpenAI, thread_id: str):
    metadata = {"example_key": "example_value"}
    response = openai_client.beta.threads.retrieve(thread_id=thread_id)
    assert isinstance(response, Thread)
    assert response.id == thread_id
    assert response.object == "thread"
    assert response.created_at is not None
    assert response.metadata == metadata


@pytest.mark.dependency(depends=["test_create_thread_without_messages"])
def test_update_thread_metadata(openai_client: OpenAI, thread_id: str):
    metadata_update = {"new_key": "new_value"}
    openai_client.beta.threads.update(thread_id, metadata=metadata_update)
    time.sleep(0.5)
    metadata_to_be = {**metadata_update, "example_key": "example_value"}
    response = openai_client.beta.threads.retrieve(thread_id=thread_id)
    assert isinstance(response, Thread)
    assert response.id == thread_id
    assert response.metadata == metadata_to_be


@pytest.mark.dependency(
    depends=["test_create_thread_without_messages", "test_get_thread"]
)
def test_delete_thread(openai_client: OpenAI, thread_id: str):
    # veryfy that the thread exists
    response = openai_client.beta.threads.retrieve(thread_id=thread_id)
    assert isinstance(response, Thread)
    assert response.id == thread_id
    # delete the thread
    response = openai_client.beta.threads.delete(thread_id=thread_id)
    assert response.id == thread_id
    assert response.deleted is True
    # verify that the thread has been deleted
    try:
        openai_client.beta.threads.retrieve(thread_id=thread_id)
    except Exception as e:
        assert e.status_code == 404
        assert "Thread not found" in str(e)
    else:
        raise AssertionError("Thread was not deleted")


# @pytest.fixture(scope="session", autouse=True)
# def cleanup(request):
#     # THIS REQUIRES A WAY TO RETIREVE ALL THREADS WHICH CURRENTLY DOES NOT EXIST IN THE API # noqa
