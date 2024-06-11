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


@pytest.mark.dependency()
def test_weaviate_integration(
    weaviate_client: weaviate.client.WeaviateClient,
):
    create_url = "http://localhost:8000/ops/web_retrieval"
    body = {
        "root_urls": ["https://quotes.toscrape.com/"],
        "constrain_to_root_domain": True,
        "max_depth": 1,
        "description": None,
    }

    response = requests.post(create_url, json=body)
    assert response.status_code == 200, f"Error: {response.json()}"
    data = response.json()
    assert "message" in data
    assert "Crawling completed successfully." == data["message"]
    assert "crawl_infos" in data
    assert len(data["crawl_infos"]) == 47
    # for all crawl_infos, check if the content is removed
    err_count = 0
    for crawl_info in data["crawl_infos"]:
        assert "<REMOVED>" == crawl_info["content"]
        if crawl_info["error"]:
            err_count += 1
    assert err_count <= 8
    # Check collection existence
    collection_name = "web_retrieval"
    assert weaviate_client.collections.exists(name=collection_name) is True

    # Insert and retrieve data to ensure functionality
    collection = weaviate_client.collections.get(name=collection_name)
    query_result = collection.query.near_text(
        query="Oscar Winning Films", limit=1
    )

    assert len(query_result.objects) == 1
    assert "content" in query_result.objects[0].properties


@pytest.mark.dependency(depends=["test_weaviate_integration"])
# @pytest.mark.skip(reason="This test is skipped unless explicitly run.")
def test_delete_collection(weaviate_client: weaviate.client.WeaviateClient):
    # Perform tasks that depend on the success of `test_weaviate_integration`
    collection_name = "web_retrieval"

    if weaviate_client.collections.exists(name=collection_name):
        weaviate_client.collections.delete(name=collection_name)
        assert (
            weaviate_client.collections.exists(name=collection_name) is False
        )
    else:
        pytest.skip(
            f"Collection '{collection_name}' does not exist, skipping the test."
        )
