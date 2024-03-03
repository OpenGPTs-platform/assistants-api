from fastapi import UploadFile
from minio import Minio
from .schemas import FileObject
import time
import uuid


def upload_file(
    minio_client: Minio, bucket_name: str, file: UploadFile
) -> FileObject:
    # Generate a unique file ID
    file_id = str(uuid.uuid4())
    file_size = len(file.file.read())
    file.file.seek(0)
    file_name = file.filename

    # Save file to MinIO
    minio_client.put_object(bucket_name, file_id, file.file, file_size)

    return FileObject(
        id=file_id,
        bytes=file_size,
        created_at=int(time.time()),
        filename=file_name,
        object="file",
        purpose="assistants",
        status="uploaded",
    )


def delete_file(minio_client: Minio, bucket_name: str, file_id: str) -> None:
    minio_client.remove_object(bucket_name, file_id)
