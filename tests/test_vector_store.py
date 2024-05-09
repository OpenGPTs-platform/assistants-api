import pytest
from openai import OpenAI
from openai.types.beta.vector_store import VectorStore
import os

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


def test_create_vector_store(openai_client: OpenAI):
    response = openai_client.beta.vector_stores.create(
        name="Example Vector Store",
        metadata={"example_key": "example_value"},
    )
    assert isinstance(response, VectorStore)
    assert response.id is not None
    assert response.created_at is not None
    assert response.name == "Example Vector Store"
    assert response.metadata == {"example_key": "example_value"}
    assert response.status == "completed"
    assert response.file_counts.total == 0
    assert response.usage_bytes == 0
