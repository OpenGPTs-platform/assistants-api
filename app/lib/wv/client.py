import weaviate
import os

WEAVIATE_HOST = os.getenv("WEAVIATE_HOST")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = weaviate.connect_to_local(
    host=WEAVIATE_HOST,
    port=8080,
    grpc_port=50051,
    headers={
        "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY"),
    },
)
