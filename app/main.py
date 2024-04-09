from fastapi import FastAPI, Request
from routers import (
    assistant_router,
    file_router,
    threads_router,
    message_router,
    run_router,
)
from routers.ops import run_ops_router, runsteps_ops_router
from lib.db.database import engine
from lib.db import models
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware


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

# TODO: Remove this in production
models.Base.metadata.drop_all(bind=engine)

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app.include_router(assistant_router.router)
app.include_router(file_router.router)
app.include_router(threads_router.router)
app.include_router(message_router.router)
app.include_router(run_router.router)

# ops routers
app.include_router(run_ops_router.router)
app.include_router(runsteps_ops_router.router)
