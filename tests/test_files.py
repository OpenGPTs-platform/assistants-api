import weaviate
import weaviate.classes as wvc
import pytest
from openai import OpenAI
from openai.types import FileObject
import os

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None
weaviate_url = os.getenv("WEAVIATE_URL") if os.getenv("WEAVIATE_URL") else None


@pytest.fixture
def openai_client():
    return OpenAI(
        base_url="http://localhost:8000",
        api_key=api_key,
    )


@pytest.mark.dependency()
def test_create_file(openai_client: OpenAI):
    with open('./tests/test.txt', 'rb') as file:
        response = openai_client.files.create(file=file, purpose="assistants")
    assert isinstance(response, FileObject)
    assert response.id == response.id
    assert response.bytes is not None
    assert response.created_at is not None
    assert response.filename == "test.txt"
    assert response.purpose == "assistants"

    weaviate_client = weaviate.connect_to_wcs(
        cluster_url=os.getenv("WEAVIATE_URL"),
        auth_credentials=None,
        headers={
            "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY"),
        },
    )
    collection = weaviate_client.collections.get(name="opengpts")
    res = collection.query.near_text(
        query="Here is a second line of text",
        limit=1,
        filters=wvc.query.Filter.by_property("file_id").equal(response.id),
    )

    assert len(res.objects) == 1
    assert "Here is a second line of text" in res.objects[0].properties["text"]


def test_create_file_pdf(openai_client: OpenAI):
    with open('./tests/test.pdf', 'rb') as file:
        response = openai_client.files.create(file=file, purpose="assistants")
    assert isinstance(response, FileObject)
    assert response.id == response.id
    assert response.bytes is not None
    assert response.created_at is not None
    assert response.filename == "test.pdf"
    assert response.purpose == "assistants"

    weaviate_client = weaviate.connect_to_wcs(
        cluster_url=os.getenv("WEAVIATE_URL"),
        auth_credentials=None,
        headers={
            "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY"),
        },
    )
    collection = weaviate_client.collections.get(name="opengpts")
    res = collection.query.near_text(
        query="Here is a second line of text",
        limit=1,
        filters=wvc.query.Filter.by_property("file_id").equal(response.id),
    )

    assert len(res.objects) == 1
    assert "Here is a second line of text" in res.objects[0].properties["text"]


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
    assert response.bytes is not None
    assert response.created_at is not None
    assert response.filename == "test.txt"
    assert response.purpose == "assistants"


@pytest.mark.dependency(depends=["test_create_file", "test_retrieve_file"])
def test_delete_file(openai_client: OpenAI):
    # Step 1: Create a file
    with open('./tests/test.txt', 'rb') as file:
        create_response = openai_client.files.create(
            file=file, purpose="assistants"
        )
    assert create_response.id is not None

    # Step 2: Retrieve the created file
    retrieve_response = openai_client.files.retrieve(create_response.id)
    assert retrieve_response.id == create_response.id

    # Step 3: Delete the file
    delete_response = openai_client.files.delete(create_response.id)
    assert delete_response.deleted is True
    assert delete_response.id == create_response.id

    # Step 4: Attempt to retrieve the deleted file
    with pytest.raises(Exception):
        openai_client.files.retrieve(create_response.id)
