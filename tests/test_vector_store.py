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


@pytest.fixture
def file_pdf(openai_client: OpenAI):
    with open("./tests/test.pdf", "rb") as file:
        return openai_client.files.create(file=file, purpose="assistants")


@pytest.fixture
def file_txt(openai_client: OpenAI):
    with open("./tests/test.txt", "rb") as file:
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


# def test_create_vector_store(openai_client: OpenAI):
#     response = openai_client.beta.vector_stores.create(
#         name="Example Vector Store",
#         metadata={"example_key": "example_value"},
#     )
#     assert isinstance(response, VectorStore)
#     assert response.id is not None
#     assert response.created_at is not None
#     assert response.name == "Example Vector Store"
#     assert response.metadata == {"example_key": "example_value"}
#     assert response.status == "completed"
#     assert response.file_counts.total == 0
#     assert response.usage_bytes == 0


# @pytest.mark.dependency()
# def test_create_vector_store_with_files(
#     openai_client: OpenAI, weaviate_client: weaviate.client.WeaviateClient
# ):
#     with open("./tests/test.txt", "rb") as file:
#         file_txt = openai_client.files.create(file=file, purpose="assistants")
#     with open("./tests/test.pdf", "rb") as file:
#         file_pdf = openai_client.files.create(file=file, purpose="assistants")

#     response = openai_client.beta.vector_stores.create(
#         name="Example Vector Store",
#         metadata={"example_key": "example_value"},
#         file_ids=[file_txt.id, file_pdf.id],
#     )

#     assert isinstance(response, VectorStore)
#     assert response.id is not None
#     assert response.file_counts.total == 2

#     # # wait untill uploads are completed
#     # max_checks = 5
#     # check_interval = 2
#     # for _ in range(max_checks):
#     #     time.sleep(check_interval)
#     #     response = openai_client.beta.vector_stores.retrieve(response.id)

#     #     assert response.status in ["in_progress", "completed"]

#     #     if response.status == "completed":
#     #         break
#     # else:
#     #     # If the loop completes without breaking, assert failure due to timeout
#     #     assert False, "Run did not complete within the expected time."

#     # assert response.usage_bytes > 5700

#     if not use_openai:
#         assert (
#             weaviate_client.collections.exists(id_to_string(response.id))
#             is True
#         )
#         print("id_to_string(response.id):", id_to_string(response.id))
#         collection = weaviate_client.collections.get(id_to_string(response.id))

#         res = collection.query.near_text(
#             query="Here is a second line of text", limit=1
#         )

#         assert len(res.objects) == 1
#         assert (
#             "Here is a second line of text"
#             in res.objects[0].properties["text"]
#         )


# @pytest.mark.dependency(depends=["test_create_vector_store"])
@pytest.mark.dependency()
def test_retrieve_vector_store(openai_client: OpenAI, vector_store_1_file):
    response = openai_client.beta.vector_stores.retrieve(
        vector_store_1_file.id
    )
    assert isinstance(response, VectorStore)
    assert response.id == vector_store_1_file.id
    assert response.name == "Example Vector Store"
    assert response.metadata == {"example_key": "example_value"}
    assert response.file_counts.total == 1


# # @pytest.mark.dependency(depends=["test_retrieve_vector_store"])
# @pytest.mark.dependency()
# def test_list_vector_stores(
#     openai_client: OpenAI, vector_store, vector_store_1_file
# ):
#     response = openai_client.beta.vector_stores.list()
#     assert isinstance(response.data, list)
#     assert len(response.data) >= 2
#     assert all(isinstance(item, VectorStore) for item in response)

#     vector_store_id = response.data[0].id
#     response = openai_client.beta.vector_stores.retrieve(vector_store_id)
#     assert isinstance(response, VectorStore)
#     assert response.id == vector_store_id