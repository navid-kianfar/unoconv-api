import os
from typing import Optional

import aiofiles
import aiobotocore.session
from botocore.config import Config as BotoConfig


class S3Storage:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1"
    ):
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY")
        self.region = region or os.getenv("S3_REGION", "us-east-1")
        
        self._session = aiobotocore.session.get_session()
        self._config = BotoConfig(signature_version='s3v4', retries={'max_attempts': 3})

    def _parse_path(self, path: str) -> tuple[str, str]:
        if path.startswith('s3://'):
            path = path[5:]
        parts = path.split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        return bucket, key

    def _get_client(self):
        return self._session.create_client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            config=self._config
        )

    async def download(self, source: str, local_path: str):
        bucket, key = self._parse_path(source)
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        async with self._get_client() as client:
            await client.download_file(bucket, key, local_path)

    async def upload(self, local_path: str, destination: str, content_type: str = "application/octet-stream"):
        bucket, key = self._parse_path(destination)
        async with self._get_client() as client:
            await client.upload_file(local_path, bucket, key)

    async def get(self, path: str) -> bytes:
        bucket, key = self._parse_path(path)
        async with self._get_client() as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            async with response['Body'] as stream:
                return await stream.read()

    async def put(self, data: bytes, destination: str, content_type: str = "application/octet-stream"):
        bucket, key = self._parse_path(destination)
        async with self._get_client() as client:
            await client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)