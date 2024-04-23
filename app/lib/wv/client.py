import weaviate
import os

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = weaviate.connect_to_wcs(
    cluster_url=WEAVIATE_URL,
    auth_credentials=None,
    headers={
        "X-OpenAI-Api-Key": OPENAI_API_KEY,
    },
)
