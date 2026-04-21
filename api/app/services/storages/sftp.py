import os
from typing import Optional

import asyncssh


class SFTPStorage:
    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_path: Optional[str] = None
    ):
        self.host = host or os.getenv("SFTP_HOST")
        self.port = port or int(os.getenv("SFTP_PORT", "22"))
        self.username = username or os.getenv("SFTP_USERNAME")
        self.password = password or os.getenv("SFTP_PASSWORD")
        self.key_path = key_path or os.getenv("SFTP_KEY_PATH")

    def _parse_path(self, path: str) -> tuple[str, str]:
        path = path.replace('sftp://', '').replace('sftp/', '')
        host = path.split('/')[0]
        remote_path = '/' + '/'.join(path.split('/')[1:])
        return host, remote_path

    def _get_connect_kwargs(self):
        kwargs = {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
        }
        if self.key_path:
            kwargs["client_keys"] = [self.key_path]
        return kwargs

    async def download(self, source: str, local_path: str):
        host, remote_path = self._parse_path(source)
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        
        connect_kwargs = self._get_connect_kwargs()
        connect_kwargs["host"] = host
        
        async with asyncssh.connect(**connect_kwargs) as conn:
            await conn.get(remote_path, local_path)

    async def upload(self, local_path: str, destination: str):
        host, remote_path = self._parse_path(destination)
        
        connect_kwargs = self._get_connect_kwargs()
        connect_kwargs["host"] = host
        
        async with asyncssh.connect(**connect_kwargs) as conn:
            await conn.put(local_path, remote_path)

    async def get(self, path: str) -> bytes:
        host, remote_path = self._parse_path(path)
        
        connect_kwargs = self._get_connect_kwargs()
        connect_kwargs["host"] = host
        
        async with asyncssh.connect(**connect_kwargs) as conn:
            async with conn.open(remote_path) as f:
                return await f.read()

    async def put(self, data: bytes, destination: str):
        host, remote_path = self._parse_path(destination)
        
        connect_kwargs = self._get_connect_kwargs()
        connect_kwargs["host"] = host
        
        async with asyncssh.connect(**connect_kwargs) as conn:
            async with conn.open(remote_path, 'w') as f:
                await f.write(data)