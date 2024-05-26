from fastapi import UploadFile
from minio import Minio
from .schemas import FileObject
import time
import uuid
import io


def upload_file(
    minio_client: Minio, bucket_name: str, file: UploadFile, file_data: bytes
) -> FileObject:
    file_id = str(uuid.uuid4())  # Generate a unique file ID
    file_name = file.filename
    file_size = len(file_data)
    file_stream = io.BytesIO(file_data)  # Create a stream from the byte data

    # Save file to MinIO
    minio_client.put_object(
        bucket_name,
        file_id,
        file_stream,
        file_size,
        metadata={"filename": file_name},
    )

    return FileObject(
        id=file_id,
        bytes=file_size,
        created_at=int(time.time()),
        filename=file_name,
        object="file",
        purpose="assistants",
        status="uploaded",
    )


def get_file(
    minio_client: Minio, bucket_name: str, file_id: str
) -> FileObject:
    # Retrieve file information
    try:
        file_stat = minio_client.stat_object(bucket_name, file_id)
        # Optional: Retrieve the metadata if needed
        filename = file_stat.metadata["x-amz-meta-filename"]

        return FileObject(
            id=file_id,
            bytes=file_stat.size,
            created_at=int(file_stat.last_modified.timestamp()),
            filename=filename,
            object="file",
            purpose="assistants",  # Adjust as necessary, possibly from metadata
            status="uploaded",  # Adjust as necessary
        )
    except Exception as e:
        print(f"Error retrieving file: {str(e)}")
        raise e


def get_file_binary(
    minio_client: Minio, bucket_name: str, file_id: str
) -> bytes:
    return minio_client.get_object(bucket_name, file_id).read()


def delete_file(minio_client: Minio, bucket_name: str, file_id: str) -> None:
    minio_client.remove_object(bucket_name, file_id)
