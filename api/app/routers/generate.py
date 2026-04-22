import os
import uuid
from typing import Optional, Annotated

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
import aiofiles


from app.services.storage_service import StorageService, get_storage_service
from app.services.thumbnail_service import ThumbnailService, ThumbnailOptions
from app.services.converter_service import ConverterService, ConversionOptions
from app.models.enums import SourceType, OutputType, ThumbnailFormat, ConversionFormat
from app.core.security import validate_api_key


router = APIRouter(prefix="/api/v1", tags=["generate"], dependencies=[Depends(validate_api_key)])


def get_storage(
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
    return get_storage_service(
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


def get_thumbnail_service() -> ThumbnailService:
    return ThumbnailService(temp_dir=os.getenv("TEMP_DIR", "/tmp/thumbnails"))


def get_converter_service() -> ConverterService:
    return ConverterService(temp_dir=os.getenv("TEMP_DIR", "/tmp/conversions"))


def cleanup_temp_files(paths: list[str]):
    """Cleanup temporary files after response is sent"""
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@router.post("/thumbnail", response_class=StreamingResponse)
async def generate_thumbnail(
    source_type: Annotated[SourceType, Form(description="Source storage type")],
    output_type: Annotated[OutputType, Form(description="Output storage type")],
    background_tasks: BackgroundTasks,
    source_path: Annotated[Optional[str], Form()] = None,
    output_path: Annotated[Optional[str], Form()] = None,
    file: UploadFile = File(None, description="File to upload"),
    width: Annotated[int, Form()] = 300,
    height: Annotated[int, Form()] = 300,
    quality: Annotated[int, Form()] = 85,
    trim: Annotated[bool, Form()] = False,
    output_format: Annotated[ThumbnailFormat, Form()] = ThumbnailFormat.PNG,
    page: Annotated[int, Form(ge=1, description="Page number for documents (default: 1)")] = 1,
    frame: Annotated[Optional[int], Form(description="Frame number for videos (default: middle)")] = None,
    # Storage credentials
    s3_endpoint_url: Optional[str] = Form(None),
    s3_access_key: Optional[str] = Form(None),
    s3_secret_key: Optional[str] = Form(None),
    s3_region: Optional[str] = Form(None),
    ftp_host: Optional[str] = Form(None),
    ftp_port: int = Form(21),
    ftp_username: Optional[str] = Form(None),
    ftp_password: Optional[str] = Form(None),
    sftp_host: Optional[str] = Form(None),
    sftp_port: int = Form(22),
    sftp_username: Optional[str] = Form(None),
    sftp_password: Optional[str] = Form(None),
    sftp_key_path: Optional[str] = Form(None),
):
    """Generate thumbnail from images, videos, and documents"""
    storage = get_storage(
        s3_endpoint_url, s3_access_key, s3_secret_key, s3_region,
        ftp_host, ftp_port, ftp_username, ftp_password,
        sftp_host, sftp_port, sftp_username, sftp_password, sftp_key_path
    )
    thumbnail_service = get_thumbnail_service()
    
    options = ThumbnailOptions(
        width=width,
        height=height,
        quality=quality,
        trim=trim,
        output_format=output_format,
        page=page,
        frame=frame
    )
    
    temp_input = None
    temp_output = None
    
    try:
        # Handle input
        if source_type == SourceType.STREAM:
            if not file:
                raise HTTPException(status_code=400, detail="File required for stream upload")
            file_bytes = await file.read()
            source_ext = file.filename.split('.')[-1] if file.filename else 'tmp'
            temp_input = f"/tmp/thumbnails/{uuid.uuid4()}.{source_ext}"
            await storage.put(file_bytes, temp_input)
        elif source_type == SourceType.LOCAL:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required for local input")
            if not os.path.exists(source_path):
                raise HTTPException(status_code=404, detail=f"Local file not found: {source_path}")
            temp_input = source_path
        elif source_type in [SourceType.S3, SourceType.FTP, SourceType.SFTP, SourceType.REMOTE]:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required")
            temp_input = f"/tmp/thumbnails/{uuid.uuid4()}_input"
            await storage.download(source_path, temp_input)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")
        
        # Generate thumbnail
        temp_output = f"/tmp/thumbnails/thumbnail_{uuid.uuid4()}.{output_format.value}"
        output_generated = await thumbnail_service.generate(temp_input, temp_output, options)
        
        # Handle output
        if output_type == OutputType.STREAM:
            async def iter_file():
                async with aiofiles.open(output_generated, 'rb') as f:
                    while chunk := await f.read(8192):
                        yield chunk
            
            # Cleanup in background
            files_to_cleanup = []
            if temp_input and temp_input != source_path:
                files_to_cleanup.append(temp_input)
            files_to_cleanup.append(output_generated)
            background_tasks.add_task(cleanup_temp_files, files_to_cleanup)
            
            return StreamingResponse(
                iter_file(),
                media_type=f"image/{output_format.value}",
                headers={"Content-Disposition": f"attachment; filename=thumbnail.{output_format.value}"}
            )
        elif output_type == OutputType.LOCAL:
            if not output_path:
                raise HTTPException(status_code=400, detail="output_path required for local output")
            # For local output, we just move/copy the file or use storage.upload
            await storage.upload(output_generated, output_path)
            return {
                "success": True,
                "message": "Thumbnail generated locally",
                "output_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
            # Cleanup non-stream outputs
            files_to_cleanup = []
            if temp_input and temp_input != source_path:
                files_to_cleanup.append(temp_input)
            if output_generated:
                files_to_cleanup.append(output_generated)
            background_tasks.add_task(cleanup_temp_files, files_to_cleanup)
            
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
# Removed immediate finally block to prevent race conditions with StreamingResponse


@router.post("/convert", response_class=StreamingResponse)
async def convert_file(
    source_type: Annotated[SourceType, Form()],
    output_type: Annotated[OutputType, Form()],
    background_tasks: BackgroundTasks,
    output_format: Annotated[ConversionFormat, Form(description="Target format")],
    source_path: Annotated[Optional[str], Form()] = None,
    output_path: Annotated[Optional[str], Form()] = None,
    file: UploadFile = File(None, description="File to upload"),
    page: Annotated[int, Form(ge=1, description="Page number for multi-page inputs")] = 1,
    quality: Annotated[int, Form()] = 85,
    width: Annotated[Optional[int], Form()] = None,
    height: Annotated[Optional[int], Form()] = None,
    # Storage credentials
    s3_endpoint_url: Optional[str] = Form(None),
    s3_access_key: Optional[str] = Form(None),
    s3_secret_key: Optional[str] = Form(None),
    s3_region: Optional[str] = Form(None),
    ftp_host: Optional[str] = Form(None),
    ftp_port: int = Form(21),
    ftp_username: Optional[str] = Form(None),
    ftp_password: Optional[str] = Form(None),
    sftp_host: Optional[str] = Form(None),
    sftp_port: int = Form(22),
    sftp_username: Optional[str] = Form(None),
    sftp_password: Optional[str] = Form(None),
    sftp_key_path: Optional[str] = Form(None),
):
    """Convert files between different formats"""
    storage = get_storage(
        s3_endpoint_url, s3_access_key, s3_secret_key, s3_region,
        ftp_host, ftp_port, ftp_username, ftp_password,
        sftp_host, sftp_port, sftp_username, sftp_password, sftp_key_path
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
        if source_type == SourceType.STREAM:
            if not file:
                raise HTTPException(status_code=400, detail="File required for stream upload")
            file_bytes = await file.read()
            source_ext = file.filename.split('.')[-1] if file.filename else 'tmp'
            temp_input = f"/tmp/conversions/{uuid.uuid4()}.{source_ext}"
            await storage.put(file_bytes, temp_input)
        elif source_type == SourceType.LOCAL:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required for local input")
            if not os.path.exists(source_path):
                raise HTTPException(status_code=404, detail=f"Local file not found: {source_path}")
            temp_input = source_path
        elif source_type in [SourceType.S3, SourceType.FTP, SourceType.SFTP, SourceType.REMOTE]:
            if not source_path:
                raise HTTPException(status_code=400, detail="source_path required")
            temp_input = f"/tmp/conversions/{uuid.uuid4()}_input"
            await storage.download(source_path, temp_input)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid source_type: {source_type}")
        
        # Convert
        temp_output = f"/tmp/conversions/converted_{uuid.uuid4()}.{output_format.value}"
        output_generated = await converter_service.convert(temp_input, temp_output, options)
        
        # Handle output
        mime_map = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
        }
        
        if output_type == OutputType.STREAM:
            async def iter_file():
                async with aiofiles.open(output_generated, 'rb') as f:
                    while chunk := await f.read(8192):
                        yield chunk
            
            # Cleanup in background
            files_to_cleanup = []
            if temp_input and temp_input != source_path:
                files_to_cleanup.append(temp_input)
            files_to_cleanup.append(output_generated)
            background_tasks.add_task(cleanup_temp_files, files_to_cleanup)
            
            return StreamingResponse(
                iter_file(),
                media_type=mime_map.get(output_format.value, "application/octet-stream"),
                headers={"Content-Disposition": f"attachment; filename=converted.{output_format.value}"}
            )
        elif output_type == OutputType.LOCAL:
            if not output_path:
                raise HTTPException(status_code=400, detail="output_path required for local output")
            await storage.upload(output_generated, output_path)
            return {
                "success": True,
                "message": f"Converted locally to {output_format.value}",
                "output_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
            # Cleanup non-stream outputs
            files_to_cleanup = []
            if temp_input and temp_input != source_path:
                files_to_cleanup.append(temp_input)
            if output_generated:
                files_to_cleanup.append(output_generated)
            background_tasks.add_task(cleanup_temp_files, files_to_cleanup)
            
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
# Removed immediate finally block to prevent race conditions with StreamingResponse