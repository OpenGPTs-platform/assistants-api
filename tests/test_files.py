import pytest
from openai import OpenAI
from openai.types import FileObject
from minio import Minio
import os

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None
weaviate_url = os.getenv("WEAVIATE_URL") if os.getenv("WEAVIATE_URL") else None
use_openai = True if os.getenv("USE_OPENAI") else False
base_url = "http://localhost:8000"

ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_URL = "localhost:9000"
BUCKET_NAME = "store"


@pytest.fixture
def minio_client():
    minio_client = Minio(
        MINIO_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        secure=False,
    )
    # Create bucket if it doesn't exist
    found = minio_client.bucket_exists(BUCKET_NAME)
    if not found:
        minio_client.make_bucket(BUCKET_NAME)
    return minio_client


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


@pytest.mark.dependency()
def test_create_file(openai_client: OpenAI, minio_client: Minio):
    with open('./tests/test.txt', 'rb') as file:
        response = openai_client.files.create(file=file, purpose="assistants")
    assert isinstance(response, FileObject)
    assert response.id == response.id
    assert response.bytes is not None
    assert response.created_at is not None
    assert response.filename == "test.txt"
    assert response.purpose == "assistants"

    if not use_openai:
        file_stat = minio_client.stat_object(BUCKET_NAME, response.id)
        assert file_stat.size > 1800
        assert file_stat.metadata["x-amz-meta-filename"] == "test.txt"


def test_create_file_pdf(openai_client: OpenAI):
    with open('./tests/test.pdf', 'rb') as file:
        response = openai_client.files.create(file=file, purpose="assistants")
    assert isinstance(response, FileObject)
    assert response.id == response.id
    assert response.bytes is not None
    assert response.created_at is not None
    assert response.filename == "test.pdf"
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
