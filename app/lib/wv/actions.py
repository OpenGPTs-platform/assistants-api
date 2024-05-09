import weaviate.classes as wvc
from lib.wv.client import client as weaviate_client
from utils.document_loader import DocumentLoader
from weaviate.collections import Collection


def id_to_string(id: int) -> str:
    # need to remove all the - from the uuid
    return str(id).replace("-", "")


def create_collection(name: str) -> Collection:
    collection = weaviate_client.collections.create(
        name=id_to_string(name),
        vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(),
        generative_config=wvc.config.Configure.Generative.openai(),
    )

    return collection


def delete_collection(name: str) -> None:
    weaviate_client.collections.delete(name=id_to_string(name))


def upload_file_chunks(
    file_data: bytes, file_name: str, file_id: str, vector_store_id: str
) -> int:
    document = DocumentLoader(file_data=file_data, file_name=file_name)
    document.read()
    chunks = document.split(text_length=300, text_overlap=100)

    collection = weaviate_client.collections.get(
        name=id_to_string(vector_store_id)
    )

    data = [{"text": chunk, "file_id": file_id} for chunk in chunks]
    collection.data.insert_many(data)

    return len(chunks)
