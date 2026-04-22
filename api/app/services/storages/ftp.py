import os
from typing import Optional

import aioftp


class FTPStorage:
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 21,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.host = host or os.getenv("FTP_HOST")
        self.port = port or int(os.getenv("FTP_PORT", "21"))
        self.username = username or os.getenv("FTP_USERNAME")
        self.password = password or os.getenv("FTP_PASSWORD")

    def _parse_path(self, path: str) -> tuple[str, str]:
        path = path.replace('ftp://', '').replace('ftps://', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        return host, remote_path

    async def download(self, source: str, local_path: str):
        host, remote_path = self._parse_path(source)
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        async with aioftp.Client(host, self.port, self.username, self.password) as client:
            await client.download(remote_path, local_path)

    async def upload(self, local_path: str, destination: str, content_type: str = "application/octet-stream"):
        host, remote_path = self._parse_path(destination)
        async with aioftp.Client(host, self.port, self.username, self.password) as client:
            await client.upload(local_path, remote_path)

    async def get(self, path: str) -> bytes:
        host, remote_path = self._parse_path(path)
        async with aioftp.Client(host, self.port, self.username, self.password) as client:
            async with client.download_stream(remote_path) as stream:
                return await stream.read()

    async def put(self, data: bytes, destination: str, content_type: str = "application/octet-stream"):
        host, remote_path = self._parse_path(destination)
        async with aioftp.Client(host, self.port, self.username, self.password) as client:
            async with client.upload_stream(remote_path) as stream:
                await stream.write(data)