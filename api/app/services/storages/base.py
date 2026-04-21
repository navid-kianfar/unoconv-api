from abc import ABC, abstractmethod
from typing import Optional


class BaseStorage(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def download(self, source: str, local_path: str):
        """Download file from source to local path"""
        pass
    
    @abstractmethod
    async def upload(self, local_path: str, destination: str, content_type: str = "application/octet-stream"):
        """Upload local file to destination"""
        pass
    
    @abstractmethod
    async def get(self, path: str) -> bytes:
        """Get file content as bytes"""
        pass
    
    @abstractmethod
    async def put(self, data: bytes, destination: str, content_type: str = "application/octet-stream"):
        """Put bytes to destination"""
        pass
    
    async def exists(self, path: str) -> bool:
        """Check if file exists (optional, default implementation tries to get)"""
        try:
            await self.get(path)
            return True
        except Exception:
            return False