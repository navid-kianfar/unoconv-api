import os
import uuid
from typing import Optional
from pathlib import Path

import aiofiles
import aiobotocore.session
from botocore.config import Config as BotoConfig


class S3Service:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
        bucket: Optional[str] = None
    ):
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY")
        self.region = region or os.getenv("S3_REGION", "us-east-1")
        self.bucket = bucket or os.getenv("S3_BUCKET")
        
        self.session = aiobotocore.session.get_session()
        
        self._config = BotoConfig(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )

    def _get_client_kwargs(self):
        kwargs = {
            'region_name': self.region,
        }
        if self.endpoint_url:
            kwargs['endpoint_url'] = self.endpoint_url
        return kwargs

    async def download_file(self, s3_path: str, local_path: str):
        await self._download(s3_path, local_path)

    async def download_bytes(self, s3_path: str) -> bytes:
        bucket, key = self._parse_s3_path(s3_path)
        
        async with self.session.create_client('s3', aws_access_key_id=self.access_key,
                                                aws_secret_access_key=self.secret_key,
                                                config=self._config,
                                                **self._get_client_kwargs()) as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            async with response['Body'] as stream:
                data = await stream.read()
                return data

    async def _download(self, s3_path: str, local_path: str):
        bucket, key = self._parse_s3_path(s3_path)
        
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        
        async with self.session.create_client('s3', aws_access_key_id=self.access_key,
                                                aws_secret_access_key=self.secret_key,
                                                config=self._config,
                                                **self._get_client_kwargs()) as client:
            await client.download_file(bucket, key, local_path)

    async def upload_file(self, local_path: str, s3_path: str):
        bucket, key = self._parse_s3_path(s3_path)
        
        async with self.session.create_client('s3', aws_access_key_id=self.access_key,
                                                aws_secret_access_key=self.secret_key,
                                                config=self._config,
                                                **self._get_client_kwargs()) as client:
            await client.upload_file(local_path, bucket, key)

    async def upload_bytes(self, data: bytes, s3_path: str, content_type: str = "image/png"):
        bucket, key = self._parse_s3_path(s3_path)
        
        async with self.session.create_client('s3', aws_access_key_id=self.access_key,
                                                aws_secret_access_key=self.secret_key,
                                                config=self._config,
                                                **self._get_client_kwargs()) as client:
            await client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type
            )

    def _parse_s3_path(self, s3_path: str) -> tuple[str, str]:
        if s3_path.startswith('s3://'):
            s3_path = s3_path[5:]
        
        parts = s3_path.split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        
        return bucket, key
