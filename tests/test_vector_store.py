import pytest
from openai import OpenAI
from openai.types.beta.vector_store import VectorStore
import os
import weaviate

# import time

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None
use_openai = True if os.getenv("USE_OPENAI") else False
base_url = "http://localhost:8000"


def id_to_string(id: int) -> str:
    # need to remove all the - from the uuid
    return str(id).replace("-", "")


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
def weaviate_client():
    return weaviate.connect_to_wcs(
        cluster_url=os.getenv("WEAVIATE_URL"),
        auth_credentials=None,
        headers={
            "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY"),
        },
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


def test_create_vector_store_with_files(
    openai_client: OpenAI, weaviate_client: weaviate.client.WeaviateClient
):
    with open("./tests/test.txt", "rb") as file:
        file_txt = openai_client.files.create(file=file, purpose="assistants")
    with open("./tests/test.pdf", "rb") as file:
        file_pdf = openai_client.files.create(file=file, purpose="assistants")

    response = openai_client.beta.vector_stores.create(
        name="Example Vector Store",
        metadata={"example_key": "example_value"},
        file_ids=[file_txt.id, file_pdf.id],
    )

    assert isinstance(response, VectorStore)
    assert response.id is not None
    assert response.file_counts.total == 2

    # # wait untill uploads are completed
    # max_checks = 5
    # check_interval = 2
    # for _ in range(max_checks):
    #     time.sleep(check_interval)
    #     response = openai_client.beta.vector_stores.retrieve(response.id)

    #     assert response.status in ["in_progress", "completed"]

    #     if response.status == "completed":
    #         break
    # else:
    #     # If the loop completes without breaking, assert failure due to timeout
    #     assert False, "Run did not complete within the expected time."

    # assert response.usage_bytes > 5700

    # if not use_openai:
    #     assert (
    #         weaviate_client.collections.exists(id_to_string(response.id))
    #         is True
    #     )

    #     collection = weaviate_client.collections.get(id_to_string(response.id))

    #     res = collection.query.near_text(
    #         query="Here is a second line of text",
    #         limit=1
    #     )

    #     assert "Here is a second line of text" in res.objects[0].properties["text"]
