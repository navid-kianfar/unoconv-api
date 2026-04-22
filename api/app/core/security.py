import os
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY_NAME = "X-API-KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def validate_api_key(api_key: Optional[str] = Security(api_key_header)):
    expected_key = os.getenv("API_KEY")
    # If no API key is set in environment, bypass authentication (for dev)
    if not expected_key:
        return api_key
    
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
