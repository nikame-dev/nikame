"""MinIO/S3 storage client wrapper."""
import aioboto3
from config import settings
import logging

logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self):
        self.session = aioboto3.Session()
        self.config = {
            "endpoint_url": f"http://{settings.MINIO_ENDPOINT}",
            "aws_access_key_id": settings.MINIO_ACCESS_KEY,
            "aws_secret_access_key": settings.MINIO_SECRET_KEY,
        }

    async def get_client(self):
        return self.session.client("s3", **self.config)

    async def upload_file(self, file_path: str, bucket: str, object_name: str):
        async with await self.get_client() as s3:
            await s3.upload_file(file_path, bucket, object_name)

    async def generate_presigned_url(self, bucket: str, object_name: str, exp: int = 3600):
        async with await self.get_client() as s3:
            return await s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': object_name}, ExpiresIn=exp)

storage_client = StorageClient()
