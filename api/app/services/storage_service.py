import os
import uuid
from typing import Optional
from enum import Enum
from pathlib import Path

import aiofiles
import aiobotocore.session
from botocore.config import Config as BotoConfig


class StorageType(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    FTP = "ftp"
    SFTP = "sftp"


class StorageService:
    def __init__(
        self,
        s3_endpoint_url: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        s3_region: str = "us-east-1",
        ftp_host: Optional[str] = None,
        ftp_port: int = 21,
        ftp_username: Optional[str] = None,
        ftp_password: Optional[str] = None,
        sftp_host: Optional[str] = None,
        sftp_port: int = 22,
        sftp_username: Optional[str] = None,
        sftp_password: Optional[str] = None,
        sftp_key_path: Optional[str] = None,
    ):
        self.s3_endpoint_url = s3_endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.s3_access_key = s3_access_key or os.getenv("S3_ACCESS_KEY")
        self.s3_secret_key = s3_secret_key or os.getenv("S3_SECRET_KEY")
        self.s3_region = s3_region or os.getenv("S3_REGION", "us-east-1")
        
        self.ftp_host = ftp_host or os.getenv("FTP_HOST")
        self.ftp_port = ftp_port or int(os.getenv("FTP_PORT", "21"))
        self.ftp_username = ftp_username or os.getenv("FTP_USERNAME")
        self.ftp_password = ftp_password or os.getenv("FTP_PASSWORD")
        
        self.sftp_host = sftp_host or os.getenv("SFTP_HOST")
        self.sftp_port = sftp_port or int(os.getenv("SFTP_PORT", "22"))
        self.sftp_username = sftp_username or os.getenv("SFTP_USERNAME")
        self.sftp_password = sftp_password or os.getenv("SFTP_PASSWORD")
        self.sftp_key_path = sftp_key_path or os.getenv("SFTP_KEY_PATH")
        
        self._s3_session = aiobotocore.session.get_session()
        self._s3_config = BotoConfig(signature_version='s3v4', retries={'max_attempts': 3})

    def _parse_s3_path(self, path: str) -> tuple[str, str]:
        if path.startswith('s3://'):
            path = path[5:]
        parts = path.split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        return bucket, key

    def _detect_storage_type(self, path: str) -> StorageType:
        if path.startswith('s3://') or '.s3.' in path or path.startswith('s3/'):
            return StorageType.S3
        elif path.startswith('sftp://') or path.startswith('sftp/'):
            return StorageType.SFTP
        elif path.startswith('ftp://') or path.startswith('ftps://'):
            return StorageType.FTP
        else:
            return StorageType.LOCAL

    async def get(self, source: str, local_path: Optional[str] = None) -> bytes:
        """Fetch file content from any source"""
        storage_type = self._detect_storage_type(source)
        
        if storage_type == StorageType.S3:
            return await self._get_s3(source)
        elif storage_type == StorageType.FTP:
            return await self._get_ftp(source)
        elif storage_type == StorageType.SFTP:
            return await self._get_sftp(source)
        else:
            return await self._get_local(source)

    async def download(self, source: str, local_path: str):
        """Download file from any source to local path"""
        storage_type = self._detect_storage_type(source)
        
        if storage_type == StorageType.S3:
            await self._download_s3(source, local_path)
        elif storage_type == StorageType.FTP:
            await self._download_ftp(source, local_path)
        elif storage_type == StorageType.SFTP:
            await self._download_sftp(source, local_path)
        else:
            await self._download_local(source, local_path)

    async def put(self, data: bytes, destination: str, content_type: str = "application/octet-stream"):
        """Upload bytes to any destination"""
        dest_type = self._detect_storage_type(destination)
        
        if dest_type == StorageType.S3:
            await self._put_s3(data, destination, content_type)
        elif dest_type == StorageType.FTP:
            await self._put_ftp(data, destination)
        else:
            await self._put_local(data, destination)

    async def upload(self, local_path: str, destination: str, content_type: str = "application/octet-stream"):
        """Upload local file to any destination"""
        dest_type = self._detect_storage_type(destination)
        
        if dest_type == StorageType.S3:
            await self._upload_s3(local_path, destination, content_type)
        elif dest_type == StorageType.FTP:
            await self._upload_ftp(local_path, destination)
        else:
            await self._upload_local(local_path, destination)

    # ==================== S3 Methods ====================
    
    def _get_s3_client(self, credentials: dict = None):
        return self._s3_session.create_client(
            's3',
            aws_access_key_id=credentials.get('access_key') if credentials else self.s3_access_key,
            aws_secret_access_key=credentials.get('secret_key') if credentials else self.s3_secret_key,
            endpoint_url=credentials.get('endpoint_url') if credentials else self.s3_endpoint_url,
            region_name=credentials.get('region') if credentials else self.s3_region,
            config=self._s3_config
        )

    async def _get_s3(self, s3_path: str) -> bytes:
        bucket, key = self._parse_s3_path(s3_path)
        async with self._get_s3_client() as client:
            response = await client.get_object(Bucket=bucket, Key=key)
            async with response['Body'] as stream:
                return await stream.read()

    async def _download_s3(self, s3_path: str, local_path: str):
        bucket, key = self._parse_s3_path(s3_path)
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        async with self._get_s3_client() as client:
            await client.download_file(bucket, key, local_path)

    async def _put_s3(self, data: bytes, s3_path: str, content_type: str):
        bucket, key = self._parse_s3_path(s3_path)
        async with self._get_s3_client() as client:
            await client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

    async def _upload_s3(self, local_path: str, s3_path: str, content_type: str):
        bucket, key = self._parse_s3_path(s3_path)
        async with self._get_s3_client() as client:
            await client.upload_file(local_path, bucket, key)

    # ==================== FTP Methods ====================

    async def _get_ftp(self, ftp_path: str) -> bytes:
        import aioftp
        path = ftp_path.replace('ftp://', '').replace('ftps://', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        async with aioftp.Client(host, self.ftp_port, self.ftp_username, self.ftp_password) as client:
            async with client.download_stream(remote_path) as stream:
                return await stream.read()

    async def _download_ftp(self, ftp_path: str, local_path: str):
        import aioftp
        path = ftp_path.replace('ftp://', '').replace('ftps://', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        
        async with aioftp.Client(host, self.ftp_port, self.ftp_username, self.ftp_password) as client:
            await client.download(remote_path, local_path)

    async def _put_ftp(self, data: bytes, ftp_path: str):
        import aioftp
        path = ftp_path.replace('ftp://', '').replace('ftps://', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        async with aioftp.Client(host, self.ftp_port, self.ftp_username, self.ftp_password) as client:
            async with client.upload_stream(remote_path) as stream:
                await stream.write(data)

    async def _upload_ftp(self, local_path: str, ftp_path: str):
        import aioftp
        path = ftp_path.replace('ftp://', '').replace('ftps://', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        async with aioftp.Client(host, self.ftp_port, self.ftp_username, self.ftp_password) as client:
            await client.upload(local_path, remote_path)

    # ==================== SFTP Methods ====================

    async def _get_sftp(self, sftp_path: str) -> bytes:
        import asyncssh
        path = sftp_path.replace('sftp://', '').replace('sftp/', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        async with asyncssh.connect(
            host, port=self.sftp_port, 
            username=self.sftp_username, 
            password=self.sftp_password,
            client_keys=[self.sftp_key_path] if self.sftp_key_path else None
        ) as conn:
            async with conn.open(remote_path) as f:
                return await f.read()

    async def _download_sftp(self, sftp_path: str, local_path: str):
        import asyncssh
        path = sftp_path.replace('sftp://', '').replace('sftp/', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        
        async with asyncssh.connect(
            host, port=self.sftp_port,
            username=self.sftp_username,
            password=self.sftp_password,
            client_keys=[self.sftp_key_path] if self.sftp_key_path else None
        ) as conn:
            await conn.get(remote_path, local_path)

    async def _put_sftp(self, data: bytes, sftp_path: str):
        import asyncssh
        path = sftp_path.replace('sftp://', '').replace('sftp/', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        async with asyncssh.connect(
            host, port=self.sftp_port,
            username=self.sftp_username,
            password=self.sftp_password,
            client_keys=[self.sftp_key_path] if self.sftp_key_path else None
        ) as conn:
            async with conn.open(remote_path, 'w') as f:
                await f.write(data)

    async def _upload_sftp(self, local_path: str, sftp_path: str):
        import asyncssh
        path = sftp_path.replace('sftp://', '').replace('sftp/', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        
        async with asyncssh.connect(
            host, port=self.sftp_port,
            username=self.sftp_username,
            password=self.sftp_password,
            client_keys=[self.sftp_key_path] if self.sftp_key_path else None
        ) as conn:
            await conn.put(local_path, remote_path)

    # ==================== Local Methods ====================

    async def _get_local(self, local_path: str) -> bytes:
        async with aiofiles.open(local_path, 'rb') as f:
            return await f.read()

    async def _download_local(self, source: str, dest: str):
        import shutil
        os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
        shutil.copy2(source, dest)

    async def _put_local(self, data: bytes, local_path: str):
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        async with aiofiles.open(local_path, 'wb') as f:
            await f.write(data)

    async def _upload_local(self, local_path: str, dest: str):
        import shutil
        os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
        shutil.copy2(local_path, dest)


def get_storage_service(
    s3_endpoint_url: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None,
    s3_region: Optional[str] = None,
    ftp_host: Optional[str] = None,
    ftp_port: int = 21,
    ftp_username: Optional[str] = None,
    ftp_password: Optional[str] = None,
    sftp_host: Optional[str] = None,
    sftp_port: int = 22,
    sftp_username: Optional[str] = None,
    sftp_password: Optional[str] = None,
    sftp_key_path: Optional[str] = None,
) -> StorageService:
    return StorageService(
        s3_endpoint_url=s3_endpoint_url,
        s3_access_key=s3_access_key,
        s3_secret_key=s3_secret_key,
        s3_region=s3_region,
        ftp_host=ftp_host,
        ftp_port=ftp_port,
        ftp_username=ftp_username,
        ftp_password=ftp_password,
        sftp_host=sftp_host,
        sftp_port=sftp_port,
        sftp_username=sftp_username,
        sftp_password=sftp_password,
        sftp_key_path=sftp_key_path,
    )
