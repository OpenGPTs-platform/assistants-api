from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from utils.tranformers import (
    db_to_pydantic_vector_store,
    db_to_pydantic_vector_store_file_batch,
)
from lib.db import crud, schemas, database
from minio import Minio
from lib.wv import actions as wv_actions
from lib.fs.store import minio_client, BUCKET_NAME
from lib.fs import actions as fs_actions
import json


router = APIRouter()


@router.post("/vector_stores", response_model=schemas.VectorStore)
def create_vector_store(
    background_tasks: BackgroundTasks,
    vector_store: schemas.VectorStoreCreate,
    db: Session = Depends(database.get_db),
    minio_client: Minio = Depends(minio_client),
):
    db_vector_store = crud.create_vector_store(
        db=db, vector_store=vector_store
    )
    vector_store_model = db_to_pydantic_vector_store(db_vector_store)
    wv_actions.create_collection(vector_store_model.id)

    # Adding the file processing to background tasks
    if vector_store.file_ids:
        background_tasks.add_task(
            process_files,
            vector_store_model,
            vector_store.file_ids,
            db,
            minio_client,
        )

    return vector_store_model


@router.post(
    "/vector_stores/{vector_store_id}/file_batches",
    response_model=schemas.VectorStoreFileBatch,
)
def create_vector_store_file_batch(
    background_tasks: BackgroundTasks,
    vector_store_id: str,
    file_batch: schemas.CreateVectorStoreFileBatchRequest,
    db: Session = Depends(database.get_db),
    minio_client: Minio = Depends(minio_client),
):
    # Check if vector store exists
    db_vector_store = crud.get_vector_store(db, vector_store_id)
    if not db_vector_store:
        raise HTTPException(status_code=404, detail="Vector store not found")
    vector_store = db_to_pydantic_vector_store(db_vector_store)

    # Create file batch
    db_file_batch = crud.create_file_batch(
        db, vector_store.id, file_batch.file_ids
    )
    file_batch_model = db_to_pydantic_vector_store_file_batch(db_file_batch)

    # Process files in the background
    background_tasks.add_task(
        process_files,
        vector_store,
        file_batch.file_ids,
        db,
        minio_client,
        file_batch_model,
    )

    return file_batch_model


def process_files(
    vector_store_model: schemas.VectorStore,
    file_ids,
    db,
    minio_client,
    vector_store_file_batch: Optional[schemas.VectorStoreFileBatch] = None,
):
    # Retrieve the existing vector store to update
    vector_store_model.file_counts.in_progress = len(file_ids)

    if vector_store_file_batch:
        vector_store_file_batch.file_counts.in_progress = len(file_ids)

    status = (
        "in_progress"
        if vector_store_model.file_counts.in_progress > 0
        else "completed"
    )
    usage_bytes = 0

    # Process each file
    for file_id in file_ids:
        crud.update_vector_store(
            db,
            vector_store_model.id,
            {
                "file_counts": vector_store_model.file_counts.model_dump(),
                "usage_bytes": usage_bytes,
                "status": status,
                "metadata": vector_store_model.metadata,
            },
        )
        if vector_store_file_batch:
            crud.update_file_batch(
                db,
                vector_store_file_batch.id,
                {
                    "file_counts": vector_store_file_batch.file_counts.model_dump(),
                    "status": status,
                },
            )
        try:
            file_data = fs_actions.get_file_binary(
                minio_client, BUCKET_NAME, file_id
            )
            file_metadata = fs_actions.get_file(
                minio_client, BUCKET_NAME, file_id
            )

            wv_actions.upload_file_chunks(
                file_data,
                file_metadata.filename,
                file_id,
                vector_store_model.id,
            )
            usage_bytes += len(file_data)
            vector_store_model.file_counts.completed += 1
            # update metadata _file_ids
            file_ids: List[str] = json.loads(
                vector_store_model.metadata["_file_ids"]
            )
            file_ids.append(file_id)
            vector_store_model.metadata["_file_ids"] = json.dumps(file_ids)
            if vector_store_file_batch:
                vector_store_file_batch.file_counts.completed += 1
        except Exception as e:
            print(
                f"Error processing file '{file_metadata.filename}': {str(e)}"
            )
            vector_store_model.file_counts.failed += 1
            if vector_store_file_batch:
                vector_store_file_batch.file_counts.failed += 1
        finally:
            vector_store_model.file_counts.in_progress -= 1
            vector_store_model.file_counts.total += 1
            if vector_store_file_batch:
                vector_store_file_batch.file_counts.in_progress -= 1
                vector_store_file_batch.file_counts.total += 1
            status = (
                "completed"
                if vector_store_model.file_counts.in_progress == 0
                else "in_progress"
            )

    status = (
        "in_progress"
        if vector_store_model.file_counts.in_progress > 0
        else "completed"
    )

    # Update the vector store with the final counts and usage bytes
    crud.update_vector_store(
        db,
        vector_store_model.id,
        {
            "file_counts": vector_store_model.file_counts.model_dump(),
            "usage_bytes": usage_bytes,
            "status": status,
            "metadata": vector_store_model.metadata,
        },
    )


@router.get(
    "/vector_stores/{vector_store_id}", response_model=schemas.VectorStore
)
def read_vector_store(
    vector_store_id: str, db: Session = Depends(database.get_db)
):
    db_vector_store = crud.get_vector_store(
        db, vector_store_id=vector_store_id
    )
    if db_vector_store is None:
        raise HTTPException(status_code=404, detail="Vector store not found")
    return db_to_pydantic_vector_store(db_vector_store)


@router.get(
    "/vector_stores",
    response_model=schemas.SyncCursorPage[schemas.VectorStore],
)
def list_vector_stores(
    db: Session = Depends(database.get_db),
    limit: int = Query(default=20, le=100),
    order: str = Query(default="desc", regex="^(asc|desc)$"),
    after: Optional[str] = None,
    before: Optional[str] = None,
):
    """
    List vector stores with optional pagination and ordering.
    - **limit**: Maximum number of results to return.
    - **order**: Sort order based on the creation time ('asc' or 'desc').
    - **after**: ID to start the list from (for pagination).
    - **before**: ID to list up to (for pagination).
    """
    vector_stores = crud.get_vector_stores(
        db=db, limit=limit, order=order, after=after, before=before
    )

    vector_store_data = [
        db_to_pydantic_vector_store(store) for store in vector_stores
    ]
    paginated_vector_stores = schemas.SyncCursorPage(data=vector_store_data)

    return paginated_vector_stores
