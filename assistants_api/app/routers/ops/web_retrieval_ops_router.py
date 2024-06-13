# ops/web_retrieval.py
from fastapi import APIRouter, Body, HTTPException
from utils.crawling import (
    crawl_websites,
    content_preprocess,
)
from lib.wv.client import client
import weaviate
from lib.db import schemas

router = APIRouter()

COLLECTION_NAME = "web_retrieval"
DEFAULT_WEB_RETRIEVAL_DESCRIPTION = "web_retrieval has not been initiated yet. Do not use this tool. To initiate it use `client.ops.web_retrieval.crawl_and_upsert(...)`"  # noqa


async def success_callback(
    crawl_info: schemas.CrawlInfo, collection: weaviate.collections.Collection
):
    print(f"Callback for URL: {crawl_info.url}\n")
    try:
        collection.data.delete_many(
            where=weaviate.classes.query.Filter.by_property("url").equal(
                crawl_info.url
            )
        )
        processed_data = content_preprocess(crawl_info)
        data_to_insert = [
            {"url": info.url, "content": info.content, "depth": info.depth}
            for info in processed_data
        ]
        collection.data.insert_many(data_to_insert)
    except Exception as e:
        print(f"Error during callback for URL {crawl_info.url}: {e}")


@router.post("/ops/web_retrieval", response_model=schemas.WebRetrievalResponse)
async def start_crawl(
    data: schemas.WebRetrievalCreate = Body(
        ..., title="Root URLs and max depth"
    ),
):
    if data.description == DEFAULT_WEB_RETRIEVAL_DESCRIPTION:
        data.description = "Web Retrieval contains information scraped from specific website domains. Use this when precise information in a website may need to be retrieved."  # noqa
        print(
            f"\n\nWARNING: WEB_RETRIEVAL_DESCRIPTION is not set. Defaulting to \"{data.description}\""  # noqa
        )  # noqa
    collection = client.collections.get(name=COLLECTION_NAME)
    if data.description:
        collection.config.update(description=data.description)

    print("Starting web retrieval...")
    try:
        crawl_infos = await crawl_websites(
            data.root_urls,
            data.constrain_to_root_domain,
            data.max_depth,
            lambda x: success_callback(x, collection),
        )

        print(f"\n\nTotal crawls: {len(crawl_infos)}")
        no_error_craws = [c for c in crawl_infos if c.error is None]
        print(f"Successful crawls count: {len(no_error_craws)}")

        # clear content from crawl_infos
        for crawl_info in crawl_infos:
            crawl_info.content = "<REMOVED>"
        return schemas.WebRetrievalResponse(
            message="Crawling completed successfully.",
            crawl_infos=crawl_infos,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# behaves more like restart
@router.delete("/ops/web_retrieval", response_model=schemas.DeleteResponse)
async def delete_collection():
    try:
        if client.collections.exists(name=COLLECTION_NAME):
            client.collections.delete(name=COLLECTION_NAME)
            # recreate the collection with no items
            del_res = schemas.DeleteResponse(
                message=f"Collection '{COLLECTION_NAME}' deleted successfully."
            )
        else:
            del_res = schemas.DeleteResponse(
                message=f"Collection '{COLLECTION_NAME}' does not exist."
            )
    except Exception as e:
        del_res = schemas.DeleteResponse(message=f"Error: {str(e)}")
    client.collections.create(
        name=COLLECTION_NAME,
        description=DEFAULT_WEB_RETRIEVAL_DESCRIPTION,
        generative_config=weaviate.classes.config.Configure.Generative.openai(),
        properties=[
            weaviate.classes.config.Property(
                name="url", data_type=weaviate.classes.config.DataType.TEXT
            ),
            weaviate.classes.config.Property(
                name="content",
                data_type=weaviate.classes.config.DataType.TEXT,
            ),
            weaviate.classes.config.Property(
                name="depth",
                data_type=weaviate.classes.config.DataType.NUMBER,
            ),
        ],
        vectorizer_config=[
            weaviate.classes.config.Configure.NamedVectors.text2vec_openai(
                name="content_and_url",
                source_properties=["content", "url"],
            )
        ],
    )
    return del_res
