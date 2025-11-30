import hashlib
import io
import uuid
from typing import Tuple
from minio import Minio
from minio.error import S3Error
from .config import settings


def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint.replace("http://", "").replace("https://", ""),
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_endpoint.startswith("https://"),
    )


def ensure_bucket_exists() -> None:
    client = get_minio_client()
    found = client.bucket_exists(settings.minio_bucket_name)
    if not found:
        client.make_bucket(settings.minio_bucket_name)


def hash_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def upload_image_bytes(
    data: bytes, content_type: str | None
) -> Tuple[str, str]:  # returns (object_key, content_hash)
    ensure_bucket_exists()
    client = get_minio_client()
    content_hash = hash_bytes(data)
    object_key = f"images/{uuid.uuid4()}"
    size = len(data)
    file_obj = io.BytesIO(data)
    client.put_object(
        settings.minio_bucket_name,
        object_key,
        data=file_obj,
        length=size,
        content_type=content_type or "application/octet-stream",
    )
    return object_key, content_hash


def get_image_bytes(object_key: str) -> bytes:
    client = get_minio_client()
    try:
        response = client.get_object(settings.minio_bucket_name, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error as exc:
        raise RuntimeError(f"Error fetching image from storage: {exc}") from exc
