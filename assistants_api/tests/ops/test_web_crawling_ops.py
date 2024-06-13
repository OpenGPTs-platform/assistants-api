from openai import OpenAI
import pytest
import weaviate
import os


# Setup Weaviate client and test URLs
WEAVIATE_HOST = "localhost"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

api_key = os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else None
use_openai = True if os.getenv("USE_OPENAI") else False
base_url = "http://localhost:8000"


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
    return weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=8080,
        grpc_port=50051,
        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY},
    )


@pytest.mark.dependency()
def test_weaviate_integration(
    openai_client: OpenAI, weaviate_client: weaviate.client.WeaviateClient
):
    crawl = openai_client.ops.web_retrieval.crawl_and_upsert(
        root_urls=["https://quotes.toscrape.com/"],
        constrain_to_root_domain=True,
        max_depth=1,
    )

    assert crawl.message == "Crawling completed successfully."
    assert len(crawl.crawl_infos) == 47

    err_count = 0
    for crawl_info in crawl.crawl_infos:
        assert crawl_info.content == "<REMOVED>"
        if crawl_info.error:
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
@pytest.mark.skip(reason="This test is skipped unless explicitly run.")
def test_change_description_and_delete_collection(
    openai_client: OpenAI, weaviate_client: weaviate.client.WeaviateClient
):
    # Test change description
    collection_name = "web_retrieval"
    test_description = "This is a test description."
    openai_client.ops.web_retrieval.crawl_and_upsert(
        root_urls=["https://quotes.toscrape.com/"],
        constrain_to_root_domain=True,
        max_depth=0,
        description=test_description,
    )

    collection = weaviate_client.collections.get(name=collection_name)
    config = collection.config.get()
    assert config.description == test_description

    # test delete (which behaves more like a reset)
    openai_client.ops.web_retrieval.delete()

    config = collection.config.get()
    assert not (config.description == test_description)
