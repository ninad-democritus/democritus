from fastapi import FastAPI
from fastapi import HTTPException
import logging
from pydantic import BaseModel
from minio import Minio
from minio.commonconfig import CopySource
import os
import uuid
from datetime import timedelta
from urllib.parse import urlparse
from typing import List


class FileUploadInfo(BaseModel):
    fileName: str
    fileType: str


class BatchUploadRequest(BaseModel):
    files: List[FileUploadInfo]


class FileUploadUrl(BaseModel):
    fileName: str
    fileId: str
    uploadUrl: str


class BatchUploadResponse(BaseModel):
    jobId: str
    uploads: List[FileUploadUrl]


class GenerateUploadUrlRequest(BaseModel):
    fileName: str
    fileType: str


class GenerateUploadUrlResponse(BaseModel):
    uploadUrl: str
    fileId: str


def get_minio_client() -> Minio:
    endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    secure = False if ":9000" in endpoint or endpoint.startswith("minio") else True
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def get_public_minio_for_presign() -> Minio:
    """Create a MinIO client configured with the public endpoint ONLY for presign.
    This client is not used for API calls, just for generating URLs with the public host.
    """
    public = os.environ.get("MINIO_PUBLIC_ENDPOINT")
    if not public:
        return get_minio_client()

    secure = False
    endpoint = public
    if public.startswith("http://") or public.startswith("https://"):
        parsed = urlparse(public)
        endpoint = parsed.netloc
        secure = parsed.scheme == "https"
    else:
        secure = not (":9000" in public or public.startswith("localhost") or public.startswith("127.0.0.1"))

    access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


app = FastAPI(title="File Upload Service")
logger = logging.getLogger("file-upload")
logging.basicConfig(level=logging.INFO)


@app.post("/v1/files/generate-upload-url", response_model=GenerateUploadUrlResponse)
def generate_upload_url(payload: GenerateUploadUrlRequest):
    bucket = os.environ.get("MINIO_BUCKET", "uploads")
    client = get_minio_client()
    try:
        if not client.bucket_exists(bucket):
            try:
                client.make_bucket(bucket)
            except Exception as exc:
                logger.warning("Bucket creation failed, proceeding: %s", exc)
    except Exception as exc:
        # Do not hard fail on bucket check; minio-init likely created it
        logger.warning("Bucket existence check failed, proceeding: %s", exc)

    file_id = str(uuid.uuid4())
    object_name = f"incoming/{file_id}/{payload.fileName}"
    
    try:
        # Generate presigned URL using internal client (for API calls to work)
        url = client.presigned_put_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(hours=1),
        )
        
        # Replace internal host with public endpoint for browser access
        public_endpoint = os.environ.get("MINIO_PUBLIC_ENDPOINT", "http://localhost")
        if "minio:9000" in url:
            url = url.replace("http://minio:9000", public_endpoint)
    except Exception as exc:
        logger.exception("Presign generation failed")
        raise HTTPException(status_code=500, detail=f"Failed to create presigned URL: {exc}")

    return GenerateUploadUrlResponse(uploadUrl=url, fileId=file_id)


@app.post("/v1/files/batch-upload-urls", response_model=BatchUploadResponse)
def generate_batch_upload_urls(payload: BatchUploadRequest):
    bucket = os.environ.get("MINIO_BUCKET", "uploads")
    client = get_minio_client()
    
    # Ensure bucket exists
    try:
        if not client.bucket_exists(bucket):
            try:
                client.make_bucket(bucket)
            except Exception as exc:
                logger.warning("Bucket creation failed, proceeding: %s", exc)
    except Exception as exc:
        logger.warning("Bucket existence check failed, proceeding: %s", exc)

    job_id = str(uuid.uuid4())
    uploads = []
    
    # Get public endpoint for URL replacement
    public_endpoint = os.environ.get("MINIO_PUBLIC_ENDPOINT", "http://localhost")
    
    for file_info in payload.files:
        file_id = str(uuid.uuid4())
        object_name = f"jobs/{job_id}/{file_id}/{file_info.fileName}"
        
        try:
            # Generate presigned URL using internal client (for API calls to work)
            url = client.presigned_put_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=timedelta(hours=1),
            )
            
            # Replace internal host with public endpoint for browser access
            if "minio:9000" in url:
                url = url.replace("http://minio:9000", public_endpoint)
                
            uploads.append(FileUploadUrl(
                fileName=file_info.fileName,
                fileId=file_id,
                uploadUrl=url
            ))
        except Exception as exc:
            logger.exception(f"Presign generation failed for {file_info.fileName}")
            raise HTTPException(status_code=500, detail=f"Failed to create presigned URL for {file_info.fileName}: {exc}")

    return BatchUploadResponse(jobId=job_id, uploads=uploads)


