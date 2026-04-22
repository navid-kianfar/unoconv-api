import os
import shutil
from typing import Optional

import aiofiles


class LocalStorage:
    """Local file storage - handles local file operations"""
    
    def __init__(self, base_path: Optional[str] = None):
        self.base_path = base_path or os.getenv("LOCAL_BASE_PATH", "")

    def _resolve_path(self, path: str) -> str:
        if self.base_path and not path.startswith('/'):
            return os.path.join(self.base_path, path)
        return path

    async def download(self, source: str, local_path: str):
        source = self._resolve_path(source)
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
        shutil.copy2(source, local_path)

    async def upload(self, local_path: str, destination: str, content_type: str = "application/octet-stream"):
        destination = self._resolve_path(destination)
        os.makedirs(os.path.dirname(destination) or '.', exist_ok=True)
        shutil.copy2(local_path, destination)

    async def get(self, path: str) -> bytes:
        path = self._resolve_path(path)
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()

    async def put(self, data: bytes, destination: str, content_type: str = "application/octet-stream"):
        destination = self._resolve_path(destination)
        os.makedirs(os.path.dirname(destination) or '.', exist_ok=True)
        async with aiofiles.open(destination, 'wb') as f:
            await f.write(data)