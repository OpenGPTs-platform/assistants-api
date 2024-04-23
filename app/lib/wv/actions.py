import weaviate.classes as wvc
from lib.wv.client import client as weaviate_client
from utils.document_loader import DocumentLoader


def upload_file_chunks(file_data: bytes, file_name: str, file_id: str) -> int:
    document = DocumentLoader(file_data=file_data, file_name=file_name)
    document.read()
    chunks = document.split(text_length=300, text_overlap=100)

    collection = None
    try:
        collection = weaviate_client.collections.get(name="opengpts")
    except Exception:
        collection = weaviate_client.collections.create(
            name="opengpts",
            vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_openai(),
        )

    data = [{"text": chunk, "file_id": file_id} for chunk in chunks]
    collection.data.insert_many(data)

    return len(chunks)
