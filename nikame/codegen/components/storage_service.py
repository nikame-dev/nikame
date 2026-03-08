"""Storage Service Codegen for NIKAME.

Generates the unified StorageService for interacting with MinIO/S3.
"""

from __future__ import annotations
from pathlib import Path
from nikame.codegen.base import BaseCodegen, CodegenContext
from nikame.config.schema import NikameConfig

class StorageServiceCodegen(BaseCodegen):
    """Generates the app/services/storage.py file."""

    NAME = "storage_service"
    
    def __init__(self, ctx: CodegenContext, config: NikameConfig) -> None:
        super().__init__(ctx, config)
        self.config = config

    def generate(self) -> list[tuple[str, str]]:
        active_modules = self.ctx.active_modules
        provider = "minio"
        if "s3" in active_modules:
            provider = "s3"
        elif "seaweedfs" in active_modules:
            provider = "seaweedfs"

        content = f'''"""
NIKAME Storage Service.
Unified interface for object storage (MinIO/S3).
"""
import os
import boto3
from botocore.client import Config

class StorageService:
    """Singleton service for object storage interactions."""
    
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            endpoint = os.getenv("STORAGE_ENDPOINT", "http://minio:9000")
            access_key = os.getenv("STORAGE_ACCESS_KEY", "minioadmin")
            secret_key = os.getenv("STORAGE_SECRET_KEY", "minioadmin")
            
            cls._client = boto3.client(
                's3',
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version='s3v4'),
                region_name='us-east-1'
            )
        return cls._client

    @classmethod
    async def upload_file(cls, bucket: str, object_name: str, file_obj):
        """Upload a file to the specified bucket."""
        client = cls.get_client()
        client.upload_fileobj(file_obj, bucket, object_name)

    @classmethod
    async def generate_presigned_url(cls, bucket: str, object_name: str, expiration=3600):
        """Generate a presigned URL for a file."""
        client = cls.get_client()
        return client.generate_presigned_url(
            'get_object',
            Params={{'Bucket': bucket, 'Key': object_name}},
            ExpiresIn=expiration
        )
'''
        return [
            ("app/services/storage.py", content),
            ("app/services/__init__.py", ""),
        ]
