import os
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
import aiofiles

from app.services.storage_service import StorageService, get_storage_service
from app.services.thumbnail_service import ThumbnailService, ThumbnailOptions
from app.services.converter_service import ConverterService, ConversionOptions


API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def require_api_key(api_key: Optional[str] = Header(None)):
    expected_key = os.getenv("API_KEY")
    if expected_key and api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


router = APIRouter(prefix="/api/v1", tags=["generate"])


def get_storage(
    s3_endpoint_url: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None,
    s3_region: Optional[str] = None,
    ftp_host: Optional[str] = None,
    ftp_port: int = 21,
    ftp_username: Optional[str] = None,
    ftp_password: Optional[str] = None,
) -> StorageService:
    return get_storage_service(
        s3_endpoint_url=s3_endpoint_url,
        s3_access_key=s3_access_key,
        s3_secret_key=s3_secret_key,
        s3_region=s3_region,
        ftp_host=ftp_host,
        ftp_port=ftp_port,
        ftp_username=ftp_username,
        ftp_password=ftp_password,
    )


def get_thumbnail_service() -> ThumbnailService:
    return ThumbnailService(temp_dir=os.getenv("TEMP_DIR", "/tmp/thumbnails"))


def get_converter_service() -> ConverterService:
    return ConverterService(temp_dir=os.getenv("TEMP_DIR", "/tmp/conversions"))


@router.post("/thumbnail", response_class=StreamingResponse, dependencies=[Depends(require_api_key)])
async def generate_thumbnail(
    source_type: str = Form(..., description="upload, file, s3, ftp"),
    source_path: Optional[str] = Form(None),
    output_type: str = Form(..., description="stream, file, s3, ftp"),
    output_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    width: int = Form(300),
    height: int = Form(300),
    quality: int = Form(85),
    trim: bool = Form(False),
    type: str = Form("thumbnail"),
    output_format: str = Form("png"),
    page: int = Form(1, ge=1, description="Page number for documents (default: 1)"),
    frame: Optional[int] = Form(None, description="Frame number for videos (default: middle)"),
    # Storage credentials
    s3_endpoint_url: Optional[str] = Form(None),
    s3_access_key: Optional[str] = Form(None),
    s3_secret_key: Optional[str] = Form(None),
    s3_region: Optional[str] = Form(None),
    ftp_host: Optional[str] = Form(None),
    ftp_port: int = Form(21),
    ftp_username: Optional[str] = Form(None),
    ftp_password: Optional[str] = Form(None),
):
    """Generate thumbnail from images, videos, and documents"""
    storage = get_storage(
        s3_endpoint_url, s3_access_key, s3_secret_key, s3_region,
        ftp_host, ftp_port, ftp_username, ftp_password
    )
    thumbnail_service = get_thumbnail_service()
    
    options = ThumbnailOptions(
        width=width,
        height=height,
        quality=quality,
        trim=trim,
        type=type,
        output_format=output_format,
        page=page,
        frame=frame
    )
    
    temp_input = None
    temp_output = None
    
    try:
        # Handle input
        if source_type == "upload":
            if not file:
                raise HTTPException(status_code=400, detail="File required for upload")
            file_bytes = await file.read()
            source_ext = file.filename.split('.')[-1] if file.filename else 'tmp'
            temp_input = f"/tmp/thumbnails/{uuid.uuid4()}.{source_ext}"
            await storage.put(file_bytes, temp_input)
        elif source_type in ["file", "local"]:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required")
            if not os.path.exists(source_path):
                raise HTTPException(status_code=404, detail=f"File not found: {source_path}")
            temp_input = source_path
        elif source_type in ["s3", "ftp"]:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required")
            temp_input = f"/tmp/thumbnails/{uuid.uuid4()}_input"
            await storage.download(source_path, temp_input)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")
        
        # Generate thumbnail
        temp_output = f"/tmp/thumbnails/thumbnail_{uuid.uuid4()}.{output_format}"
        output_generated = await thumbnail_service.generate(temp_input, temp_output, options)
        
        # Handle output
        if output_type == "stream":
            async def iter_file():
                async with aiofiles.open(output_generated, 'rb') as f:
                    while chunk := await f.read(8192):
                        yield chunk
            
            return StreamingResponse(
                iter_file(),
                media_type=f"image/{output_format}",
                headers={"Content-Disposition": f"attachment; filename=thumbnail.{output_format}"}
            )
        elif output_type in ["file", "local"]:
            if not output_path:
                raise HTTPException(status_code=400, detail="output_path required for file output")
            await storage.upload(output_generated, output_path)
            return {
                "success": True,
                "message": "Thumbnail generated",
                "output_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
        elif output_type in ["s3", "ftp"]:
            if not output_path:
                raise HTTPException(status_code=400, detail="output_path required")
            await storage.upload(output_generated, output_path, f"image/{output_format}")
            return {
                "success": True,
                "message": f"Thumbnail uploaded to {output_type}: {output_path}",
                "output_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
        else:
            raise HTTPException(status_code=400, detail=f"Invalid output_type: {output_type}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for path in [temp_input, temp_output]:
            if path and os.path.exists(path) and not path.startswith('/tmp/thumbnails/'):
                pass
            elif path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass


@router.post("/convert", response_class=StreamingResponse, dependencies=[Depends(require_api_key)])
async def convert_file(
    source_type: str = Form(...),
    source_path: Optional[str] = Form(None),
    output_type: str = Form(...),
    output_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    output_format: str = Form(..., description="Target format: pdf, png, jpg, docx, xlsx, etc."),
    page: int = Form(1, ge=1, description="Page number for multi-page inputs"),
    quality: int = Form(85),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    # Storage credentials
    s3_endpoint_url: Optional[str] = Form(None),
    s3_access_key: Optional[str] = Form(None),
    s3_secret_key: Optional[str] = Form(None),
    s3_region: Optional[str] = Form(None),
    ftp_host: Optional[str] = Form(None),
    ftp_port: int = Form(21),
    ftp_username: Optional[str] = Form(None),
    ftp_password: Optional[str] = Form(None),
):
    """Convert files between different formats"""
    storage = get_storage(
        s3_endpoint_url, s3_access_key, s3_secret_key, s3_region,
        ftp_host, ftp_port, ftp_username, ftp_password
    )
    converter_service = get_converter_service()
    
    options = ConversionOptions(
        output_format=output_format,
        quality=quality,
        width=width,
        height=height,
        page=page
    )
    
    temp_input = None
    temp_output = None
    
    try:
        # Handle input
        if source_type == "upload":
            if not file:
                raise HTTPException(status_code=400, detail="File required for upload")
            file_bytes = await file.read()
            source_ext = file.filename.split('.')[-1] if file.filename else 'tmp'
            temp_input = f"/tmp/conversions/{uuid.uuid4()}.{source_ext}"
            await storage.put(file_bytes, temp_input)
        elif source_type in ["file", "local"]:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required")
            if not os.path.exists(source_path):
                raise HTTPException(status_code=404, detail=f"File not found: {source_path}")
            temp_input = source_path
        elif source_type in ["s3", "ftp"]:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required")
            temp_input = f"/tmp/conversions/{uuid.uuid4()}_input"
            await storage.download(source_path, temp_input)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")
        
        # Convert
        temp_output = f"/tmp/conversions/converted_{uuid.uuid4()}.{output_format}"
        output_generated = await converter_service.convert(temp_input, temp_output, options)
        
        # Handle output
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
        }
        
        if output_type == "stream":
            async def iter_file():
                async with aiofiles.open(output_generated, 'rb') as f:
                    while chunk := await f.read(8192):
                        yield chunk
            
            return StreamingResponse(
                iter_file(),
                media_type=mime_map.get(output_format, "application/octet-stream"),
                headers={"Content-Disposition": f"attachment; filename=converted.{output_format}"}
            )
        elif output_type in ["file", "local"]:
            if not output_path:
                raise HTTPException(status_code=400, detail="output_path required")
            await storage.upload(output_generated, output_path)
            return {
                "success": True,
                "message": f"Converted to {output_format}",
                "output_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
        elif output_type in ["s3", "ftp"]:
            if not output_path:
                raise HTTPException(status_code=400, detail="output_path required")
            content_type = mime_map.get(output_format, "application/octet-stream")
            await storage.upload(output_generated, output_path, content_type)
            return {
                "success": True,
                "message": f"Converted and uploaded to {output_type}: {output_path}",
                "output_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
        else:
            raise HTTPException(status_code=400, detail=f"Invalid output_type: {output_type}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for path in [temp_input, temp_output]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "thumbnail-convert-api"}