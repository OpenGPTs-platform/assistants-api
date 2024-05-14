import pytest
from openai import OpenAI
from openai.types.beta.vector_store import VectorStore
import os
import weaviate
import json
import time

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


@pytest.fixture
def file_pdf(openai_client: OpenAI):
    with open("./assets/test.pdf", "rb") as file:
        return openai_client.files.create(file=file, purpose="assistants")


@pytest.fixture
def file_txt(openai_client: OpenAI):
    with open("./assets/test.txt", "rb") as file:
        return openai_client.files.create(file=file, purpose="assistants")


@pytest.fixture
def vector_store(openai_client: OpenAI):
    return openai_client.beta.vector_stores.create(
        name="Example Vector Store",
        metadata={"example_key": "example_value"},
    )


@pytest.fixture
def vector_store_1_file(openai_client: OpenAI, file_txt):
    return openai_client.beta.vector_stores.create(
        name="Example Vector Store",
        metadata={"example_key": "example_value"},
        file_ids=[file_txt.id],
    )


@pytest.fixture
def vector_store_2_files(openai_client: OpenAI, file_txt, file_pdf):
    return openai_client.beta.vector_stores.create(
        name="Example Vector Store",
        metadata={"example_key": "example_value"},
        file_ids=[file_txt.id, file_pdf.id],
    )


@pytest.mark.dependency()
def test_create_vector_store(openai_client: OpenAI):
    response = openai_client.beta.vector_stores.create(
        name="Example Vector Store",
        metadata={"example_key": "example_value"},
    )
    assert isinstance(response, VectorStore)
    assert response.id is not None
    assert response.created_at is not None
    assert response.name == "Example Vector Store"
    assert response.metadata["example_key"] == "example_value"
    assert response.status == "completed"
    assert response.file_counts.total == 0
    assert response.usage_bytes == 0
    if not use_openai:
        assert response.metadata == {
            "example_key": "example_value",
            "_file_ids": "[]",
        }


@pytest.mark.dependency(depends=["test_create_vector_store"])
def test_retrieve_vector_store(openai_client: OpenAI, vector_store_1_file):
    response = openai_client.beta.vector_stores.retrieve(
        vector_store_1_file.id
    )
    assert isinstance(response, VectorStore)
    assert response.id == vector_store_1_file.id
    assert response.name == "Example Vector Store"
    assert response.metadata["example_key"] == "example_value"
    assert (
        response.file_counts.in_progress == 1
        or response.file_counts.completed == 1
    )


@pytest.mark.dependency(
    depends=["test_create_vector_store", "test_retrieve_vector_store"]
)
def test_create_vector_store_with_files(
    openai_client: OpenAI,
    weaviate_client: weaviate.client.WeaviateClient,
    file_txt,
    file_pdf,
):
    response = openai_client.beta.vector_stores.create(
        name="Example Vector Store",
        metadata={"example_key": "example_value"},
        file_ids=[file_txt.id, file_pdf.id],
    )

    assert isinstance(response, VectorStore)
    assert response.id is not None
    if not use_openai:
        assert response.metadata == {
            "example_key": "example_value",
            "_file_ids": "[]",
        }
    # assert response.file_counts.total == 2

    # wait untill uploads are completed
    max_checks = 5
    check_interval = 2
    for _ in range(max_checks):
        time.sleep(check_interval)
        response = openai_client.beta.vector_stores.retrieve(response.id)

        print("\n\n\nresponse", response)

        assert response.status in ["in_progress", "completed"]

        if response.status == "completed":
            break
    else:
        # If the loop completes without breaking, assert failure due to timeout
        assert False, "Run did not complete within the expected time."

    assert response.usage_bytes > 4000

    if not use_openai:
        assert (
            weaviate_client.collections.exists(id_to_string(response.id))
            is True
        )
        assert "_file_ids" in response.metadata
        file_ids = json.loads(response.metadata["_file_ids"])
        assert file_pdf.id in file_ids
        assert file_txt.id in file_ids
        print("id_to_string(response.id):", id_to_string(response.id))
        collection = weaviate_client.collections.get(id_to_string(response.id))

        res = collection.query.near_text(
            query="Here is a second line of text", limit=1
        )

        assert len(res.objects) == 1
        assert (
            "Here is a second line of text"
            in res.objects[0].properties["text"]
        )


@pytest.mark.dependency(depends=["test_retrieve_vector_store"])
def test_list_vector_stores(
    openai_client: OpenAI, vector_store, vector_store_1_file
):
    response = openai_client.beta.vector_stores.list()
    assert isinstance(response.data, list)
    assert len(response.data) >= 2
    assert all(isinstance(item, VectorStore) for item in response)

    vector_store_id = response.data[0].id
    response = openai_client.beta.vector_stores.retrieve(vector_store_id)
    assert isinstance(response, VectorStore)
    assert response.id == vector_store_id


@pytest.mark.dependency(depends=["test_list_vector_stores"])
def test_list_vector_stores_limit_and_order(openai_client: OpenAI):
    # get the vector stores in ascending order
    vs0 = openai_client.beta.vector_stores.create(name="vs0")
    time.sleep(0.5)
    openai_client.beta.vector_stores.create(name="vs1")
    time.sleep(1)
    openai_client.beta.vector_stores.create(name="vs2")
    asc_response = openai_client.beta.vector_stores.list(
        order='asc', after=vs0.id
    )
    assert isinstance(asc_response.data, list)
    assert len(asc_response.data) >= 2
    # find index of vs1
    vs1_index = None
    for i, vs in enumerate(asc_response.data):
        if vs.name == "vs1":
            vs1_index = i
            break
    else:
        assert False, "Should have found vs1 in the list"

    assert (
        asc_response.data[vs1_index].created_at
        < asc_response.data[vs1_index + 1].created_at
    ), "Vector stores should be in ascending order"

    # get only the first vector store in ascending order
    response = openai_client.beta.vector_stores.list(
        limit=1, order='asc', after=vs0.id
    )
    assert len(response.data) == 1, "Should retrieve at least one vector store"
    assert (
        response.data[0].id == asc_response.data[0].id
    ), "Should retrieve the first vector store"


@pytest.mark.dependency(depends=["test_list_vector_stores"])
def test_list_vector_stores_pagination_after(openai_client: OpenAI):
    # List the first batch to get an ID to use for 'after'
    initial_response = openai_client.beta.vector_stores.list(
        limit=1, order='asc'
    )
    assert (
        len(initial_response.data) == 1
    ), "Should retrieve at least one vector store"

    # Use the ID of the first vector store to list subsequent stores
    after_item = initial_response.data[0]
    subsequent_response = openai_client.beta.vector_stores.list(
        limit=1, order='asc', after=after_item.id
    )
    assert len(subsequent_response.data) == 1
    assert (
        subsequent_response.data[0].id != after_item.id
    ), "Should not retrieve the initial vector store"
    assert (
        subsequent_response.data[0].created_at > after_item.created_at
    ), "Should retrieve vector stores after the specified ID"


@pytest.mark.dependency(depends=["test_retrieve_vector_store"])
def test_add_file_vector_store(openai_client: OpenAI, vector_store, file_txt):
    assert vector_store.file_counts.total == 0
    assert vector_store.usage_bytes == 0
    openai_client.beta.vector_stores.file_batches.create(
        vector_store_id=vector_store.id, file_ids=[file_txt.id]
    )
    # wait untill uploads are completed
    max_checks = 5
    check_interval = 2
    for _ in range(max_checks):
        time.sleep(check_interval)
        vector_store = openai_client.beta.vector_stores.retrieve(
            vector_store.id
        )

        assert vector_store.status in ["in_progress", "completed"]

        if vector_store.status == "completed":
            break
    else:
        # If the loop completes without breaking, assert failure due to timeout
        assert False, "Run did not complete within the expected time."

    assert vector_store.usage_bytes > 100
    assert vector_store.status == "completed"
    assert vector_store.file_counts.total == 1
    assert vector_store.file_counts.completed == 1
