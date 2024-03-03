import pytest
from openai import OpenAI
from openai.types import FileObject

# import os


# Assuming the openai_client fixture is defined as in the provided example
@pytest.fixture
def openai_client():
    return OpenAI(
        base_url="http://localhost:8000",
        # api_key=os.getenv("OPENAI_API_KEY"),
    )


# @pytest.mark.dependency(depends=["test_create_assistant"])
@pytest.mark.dependency()
def test_create_file(openai_client: OpenAI):
    with open('./tests/test.txt', 'rb') as file:
        response = openai_client.files.create(file=file, purpose="assistants")

    assert isinstance(response, FileObject)
    assert response.id == response.id
    assert response.bytes == 73
    assert response.created_at is not None
    assert response.filename == "test.txt"
    assert response.purpose == "assistants"


@pytest.mark.dependency(depends=["test_create_file"])
def test_retrieve_file(openai_client: OpenAI):
    # Assuming you have a file ID to test with
    with open('./tests/test.txt', 'rb') as file:
        file_created = openai_client.files.create(
            file=file, purpose="assistants"
        )
    response = openai_client.files.retrieve(file_created.id)

    assert isinstance(response, FileObject)
    assert response.id == file_created.id
    assert response.bytes == 73
    assert response.created_at is not None
    assert response.filename == "test.txt"
    assert response.purpose == "assistants"
