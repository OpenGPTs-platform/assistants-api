# ops/web_retrieval.py
from fastapi import APIRouter, Body, HTTPException
from utils.crawling import (
    CrawlInfo,
    crawl_websites,
    content_preprocess,
)
from lib.wv.client import client
import weaviate
from lib.db import schemas

router = APIRouter()


async def success_callback(
    crawl_info: CrawlInfo, collection: weaviate.collections.Collection
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
    collection_name = "web_retrieval"

    if client.collections.exists(name=collection_name):
        collection = client.collections.get(name=collection_name)
        if data.description:
            collection.config.update(description=data.description)
    else:
        data.description = "Web Retrieval contains information scraped from specific website domains. Use this when precise information in a website may need to be retrieved."  # noqa
        print(
            f"\n\nWARNING: WEB_RETRIEVAL_DESCRIPTION is not set. Defaulting to \"{data.description}\""  # noqa
        )  # noqa
        collection = client.collections.create(
            name=collection_name,
            description=data.description,
            vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai(),  # noqa
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
        )

    print("Starting web retrieval...")
    try:
        result = await crawl_websites(
            data.root_urls,
            data.max_depth,
            lambda x: success_callback(x, collection),
        )
        links_upserted = [info.url for info in result]
        print(f"Links upserted count: {len(links_upserted)}")
        return schemas.WebRetrievalResponse(
            message="Crawling completed successfully.",
            links_upserted=links_upserted,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
