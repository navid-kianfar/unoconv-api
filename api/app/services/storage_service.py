import os
from typing import Optional

from app.services.storages.base import BaseStorage
from app.services.storages.local import LocalStorage
from app.services.storages.s3 import S3Storage
from app.services.storages.ftp import FTPStorage
from app.services.storages.sftp import SFTPStorage
from app.services.storages.remote import RemoteStorage


class StorageService:
    """
    Unified storage service that delegates to specific storage backends
    based on the path scheme.
    """
    
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
        self._s3 = S3Storage(s3_endpoint_url, s3_access_key, s3_secret_key, s3_region)
        self._ftp = FTPStorage(ftp_host, ftp_port, ftp_username, ftp_password)
        self._sftp = SFTPStorage(sftp_host, sftp_port, sftp_username, sftp_password, sftp_key_path)
        self._local = LocalStorage()
        self._remote = RemoteStorage()

    def _detect_backend(self, path: str) -> BaseStorage:
        """Detect which storage backend to use based on the path"""
        if path.startswith('s3://') or '.s3.' in path or path.startswith('s3/'):
            return self._s3
        elif path.startswith('sftp://') or path.startswith('sftp/'):
            return self._sftp
        elif path.startswith('ftp://') or path.startswith('ftps://'):
            return self._ftp
        elif path.startswith('http://') or path.startswith('https://'):
            return self._remote
        else:
            return self._local

    async def download(self, source: str, local_path: str):
        """Download file from source to local path"""
        backend = self._detect_backend(source)
        await backend.download(source, local_path)

    async def upload(self, local_path: str, destination: str, content_type: str = "application/octet-stream"):
        """Upload local file to destination"""
        backend = self._detect_backend(destination)
        await backend.upload(local_path, destination, content_type)

    async def get(self, path: str) -> bytes:
        """Get file content as bytes"""
        backend = self._detect_backend(path)
        return await backend.get(path)

    async def put(self, data: bytes, destination: str, content_type: str = "application/octet-stream"):
        """Put bytes to destination"""
        backend = self._detect_backend(destination)
        await backend.put(data, destination, content_type)


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