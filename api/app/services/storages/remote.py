import os
from typing import Optional, Union

import aiofiles
import aiohttp


class RemoteStorage:
    """Remote URL storage - handles HTTP/HTTPS file downloads and uploads"""
    
    def __init__(
        self,
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
        timeout: int = 300
    ):
        self.auth_username = auth_username or os.getenv("REMOTE_AUTH_USERNAME")
        self.auth_password = auth_password or os.getenv("REMOTE_AUTH_PASSWORD")
        self.timeout = timeout

    def _parse_url(self, url: str) -> str:
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return f"https://{url}"

    def _get_auth(self, url: str):
        if self.auth_username:
            return aiohttp.BasicAuth(self.auth_username, self.auth_password)
        return None

    async def download(self, source: str, local_path: str):
        url = self._parse_url(source)
        auth = self._get_auth(url)
        
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, auth=auth) as response:
                response.raise_for_status()
                async with aiofiles.open(local_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        await f.write(chunk)

    async def upload(self, local_path: str, destination: str, content_type: str = "application/octet-stream"):
        url = self._parse_url(destination)
        auth = self._get_auth(url)
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        async with aiofiles.open(local_path, 'rb') as f:
            data = await f.read()
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {"Content-Type": content_type}
            async with session.put(url, data=data, auth=auth, headers=headers) as response:
                response.raise_for_status()

    async def get(self, url: str) -> bytes:
        url = self._parse_url(url)
        auth = self._get_auth(url)
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, auth=auth) as response:
                response.raise_for_status()
                return await response.read()

    async def put(self, data: bytes, destination: str, content_type: str = "application/octet-stream"):
        url = self._parse_url(destination)
        auth = self._get_auth(url)
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {"Content-Type": content_type}
            async with session.put(url, data=data, auth=auth, headers=headers) as response:
                response.raise_for_status()