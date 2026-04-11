import boto3
from botocore.config import Config
from app.core.settings import settings

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version="s3v4")
        )

    def create_presigned_post(self, object_name: str, fields: dict = None, conditions: list = None, expiration: int = 3600):
        """Generate a presigned URL form post to upload a file to a bucket"""
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=settings.S3_BUCKET_NAME,
                Key=object_name,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration
            )
        except Exception as e:
            # log or handle error
            return None
        return response

    def create_presigned_url(self, object_name: str, expiration: int = 3600):
        """Generate a presigned URL to share an S3 object"""
        try:
            response = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET_NAME, "Key": object_name},
                ExpiresIn=expiration
            )
        except Exception as e:
            return None
        return response

s3_service = S3Service()
