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
def test_create_file(openai_client: OpenAI):
    with open('./tests/test.txt', 'rb') as file:
        response = openai_client.files.create(file=file, purpose="assistants")

    assert isinstance(response, FileObject)
    assert response.id is not None
    assert response.created_at is not None
    assert response.bytes is not None
    assert response.filename is not None
    assert response.purpose == "assistants"
