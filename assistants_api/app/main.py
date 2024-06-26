from fastapi import FastAPI, Request
from routers import (
    assistant_router,
    file_router,
    threads_router,
    message_router,
    run_router,
    runsteps_router,
    vectorstore_router,
)
from routers.ops import (
    run_ops_router,
    runsteps_ops_router,
    web_retrieval_ops_router,
)
from lib.db.database import engine
from lib.db import models
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from lib.wv.client import client as wv_client
import weaviate


class RawBodyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        print(f"Raw body: {body}")
        response = await call_next(request)
        return response


load_dotenv()

app = FastAPI()

app.add_middleware(
    RawBodyMiddleware,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not wv_client.collections.exists(name="web_retrieval"):
    print("Creating web retrieval collection...")
    wv_client.collections.create(
        name=web_retrieval_ops_router.COLLECTION_NAME,
        description=web_retrieval_ops_router.DEFAULT_WEB_RETRIEVAL_DESCRIPTION,
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

# TODO: Remove this in production
models.Base.metadata.drop_all(bind=engine)

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app.include_router(assistant_router.router)
app.include_router(file_router.router)
app.include_router(threads_router.router)
app.include_router(message_router.router)
app.include_router(run_router.router)
app.include_router(runsteps_router.router)
app.include_router(vectorstore_router.router)

# ops routers
app.include_router(run_ops_router.router)
app.include_router(runsteps_ops_router.router)
app.include_router(web_retrieval_ops_router.router)
