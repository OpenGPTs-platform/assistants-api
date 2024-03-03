from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Path
from minio import Minio, S3Error
from lib.fs import actions
from lib.fs.store import minio_client, BUCKET_NAME
from lib.fs.schemas import FileObject, FileDeleted
from lib.db.database import get_db
from typing_extensions import Literal
from sqlalchemy.orm import Session
from lib.db import crud

router = APIRouter()


@router.post("/files", response_model=FileObject)
async def create_file(
    file: UploadFile = File(...),
    purpose: Literal["fine-tune", "assistants"] = File(...),
    db: Session = Depends(get_db),
    minio_client: Minio = Depends(minio_client),
):
    if purpose not in ["fine-tune", "assistants"]:
        raise HTTPException(status_code=400, detail="Invalid purpose")

    uploaded_file = actions.upload_file(
        minio_client=minio_client, bucket_name=BUCKET_NAME, file=file
    )

    crud.create_file(db=db, file=uploaded_file)

    return uploaded_file


@router.get("/files/{file_id}", response_model=FileObject)
async def get_file(
    file_id: str = Path(..., description="The ID of the file to retrieve"),
    db: Session = Depends(get_db),
    minio_client: Minio = Depends(minio_client),
):
    # Retrieve file metadata from the database
    file_metadata = crud.get_file(db=db, file_id=file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    # # Optional: Retrieve file contents from MinIO
    # response = minio_client.get_object(BUCKET_NAME, file_id)
    # file_content = response.read()

    # Return file metadata
    return file_metadata


@router.delete("/files/{file_id}", response_model=FileDeleted)
async def delete_file(
    file_id: str = Path(..., description="The ID of the file to delete"),
    db: Session = Depends(get_db),
    minio_client: Minio = Depends(minio_client),
):
    # Verify if the file exists in the database
    file_metadata = crud.get_file(db=db, file_id=file_id)
    if not file_metadata:
        raise HTTPException(status_code=404, detail="File not found")

    # Attempt to delete the file from MinIO
    try:
        actions.delete_file(
            minio_client=minio_client, bucket_name=BUCKET_NAME, file_id=file_id
        )
    except S3Error as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete file from storage: {e}"
        )

    # Delete the file metadata from the database
    crud.delete_file(db=db, file_id=file_id)

    return FileDeleted(id=file_id, deleted=True, object="file")
