import os
from minio import Minio

ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY')
SECRET_KEY = os.getenv('MINIO_SECRET_KEY')
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT')

minio_client = Minio(
    MINIO_ENDPOINT, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False
)
