from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from utils.tranformers import db_to_pydantic_vector_store
from lib.db import crud, schemas, database
from minio import Minio
from lib.wv import actions as wv_actions
from lib.fs.store import minio_client, BUCKET_NAME
from lib.fs import actions as fs_actions


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
            db_vector_store.id,
            vector_store.file_ids,
            db,
            minio_client,
        )

    return vector_store_model


def process_files(vector_store_id, file_ids, db, minio_client):
    # Retrieve the existing vector store to update
    file_counts = schemas.FileCounts(
        cancelled=0,
        completed=0,
        failed=0,
        in_progress=len(file_ids),
        total=len(file_ids),
    )
    usage_bytes = 0

    # Process each file
    for file_id in file_ids:
        crud.update_vector_store(
            db,
            vector_store_id,
            {
                "file_counts": file_counts.model_dump(),
                "usage_bytes": usage_bytes,
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
                file_data, file_metadata.filename, file_id, vector_store_id
            )
            usage_bytes += len(file_data)
            file_counts.completed += 1
        except Exception as e:
            print(
                f"Error processing file '{file_metadata.filename}': {str(e)}"
            )
            file_counts.failed += 1
        finally:
            file_counts.in_progress -= 1

    # Update the vector store with the final counts and usage bytes
    crud.update_vector_store(
        db,
        vector_store_id,
        {
            "file_counts": file_counts.model_dump(),
            "usage_bytes": usage_bytes,
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
