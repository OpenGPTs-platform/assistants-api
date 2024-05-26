from typing import List
import weaviate
import os
import math

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
weaviate_client = weaviate.connect_to_local(
    host=WEAVIATE_HOST,
    port=8080,
    grpc_port=50051,
    headers={
        "X-OpenAI-Api-Key": OPENAI_API_KEY,
    },
)

LIMIT = 2


def id_to_string(id: int) -> str:
    # need to remove all the - from the uuid
    return str(id).replace("-", "")


def retrieve_file_chunks(vector_store_ids: List[str], query: str) -> List[str]:
    chunks = []
    for vector_store_id in vector_store_ids:
        collection = None
        if weaviate_client.collections.exists(
            name=id_to_string(vector_store_id)
        ):
            collection = weaviate_client.collections.get(
                name=id_to_string(vector_store_id)
            )
        else:
            raise Exception(f"Collection {vector_store_id} does not exist.")

        retrieve_file_chunks = collection.query.near_text(
            query=query,
            limit=math.ceil(LIMIT / len(vector_store_ids)),
        )
        print("RETRIEVE FILE CHUNKS: ", retrieve_file_chunks)

        chunks.extend(
            [
                chunk.properties["text"]
                for chunk in retrieve_file_chunks.objects
            ]
        )

    return chunks
