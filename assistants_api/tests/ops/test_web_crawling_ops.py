import pytest
import weaviate
import os
import requests


# Setup Weaviate client and test URLs
WEAVIATE_HOST = "localhost"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@pytest.fixture
def weaviate_client():
    return weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=8080,
        grpc_port=50051,
        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
    )


def test_weaviate_integration(
    weaviate_client: weaviate.client.WeaviateClient,
):
    create_url = "http://localhost:8000/ops/web_retrieval"
    body = {
        "root_urls": ["https://www.scrapethissite.com/faq/"],
        "max_depth": 1,
    }

    response = requests.post(create_url, json=body)
    assert response.status_code == 200, f"Error: {response.json()}"
    data = response.json()
    assert "message" in data
    assert "Crawling completed successfully." == data["message"]
    assert "links_upserted" in data
    assert len(data["links_upserted"]) == 6
    # Check collection existence
    collection_name = "web_retrieval"
    assert weaviate_client.collections.exists(name=collection_name) is True

    # Insert and retrieve data to ensure functionality
    collection = weaviate_client.collections.get(name=collection_name)
    query_result = collection.query.near_text(
        query="Oscar Winning Films", limit=1
    )

    assert len(query_result.objects) == 1
    assert "AJAX" in query_result.objects[0].properties["content"]
