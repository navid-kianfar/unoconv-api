import os
import json
import asyncio
import logging
from typing import Optional

import aiofiles
import aiohttp

from app.services.storage_service import StorageService, get_storage_service
from app.services.thumbnail_service import ThumbnailService, ThumbnailOptions
from app.services.converter_service import ConverterService, ConversionOptions
from worker.queue import JobData, JobResult, QueueConfig


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobProcessor:
    def __init__(self, config: QueueConfig):
        self.config = config
        self.storage: Optional[StorageService] = None
        self.thumbnail_service: Optional[ThumbnailService] = None
        self.converter_service: Optional[ConverterService] = None

    async def initialize(self):
        self.storage = get_storage_service()
        self.thumbnail_service = ThumbnailService(temp_dir=os.getenv("TEMP_DIR", "/tmp/thumbnails"))
        self.converter_service = ConverterService(temp_dir=os.getenv("TEMP_DIR", "/tmp/conversions"))
        logger.info("JobProcessor initialized")

    async def process_thumbnail(self, job_data: JobData) -> JobResult:
        job_id = job_data.job_id or str(uuid.uuid4())
        
        temp_input = None
        temp_output = None
        
        try:
            source = job_data.source
            output = job_data.output
            options = job_data.options
            
            # Build thumbnail options
            thumbnail_options = ThumbnailOptions(
                width=options.get("width", 300),
                height=options.get("height", 300),
                quality=options.get("quality", 85),
                trim=options.get("trim", False),
                type=options.get("type", "thumbnail"),
                output_format=options.get("output_format", "png"),
                page=options.get("page", 1),
                frame=options.get("frame")
            )
            
            # Download input
            if source["type"] == "upload":
                # For worker, upload means base64 encoded data in the payload
                import base64
                file_bytes = base64.b64decode(source.get("data", ""))
                temp_input = f"/tmp/thumbnails/{job_id}_input"
                async with aiofiles.open(temp_input, 'wb') as f:
                    await f.write(file_bytes)
            else:
                temp_input = f"/tmp/thumbnails/{job_id}_input"
                await self.storage.download(source["path"], temp_input)
            
            # Generate thumbnail
            output_ext = thumbnail_options.output_format.value
            temp_output = f"/tmp/thumbnails/thumbnail_{job_id}.{output_ext}"
            
            output_path = await self.thumbnail_service.generate(
                temp_input, temp_output, thumbnail_options
            )
            
            # Upload output
            if output["type"] == "stream":
                # Return as base64
                async with aiofiles.open(output_path, 'rb') as f:
                    data = await f.read()
                import base64
                encoded = base64.b64encode(data).decode('utf-8')
                return JobResult(
                    success=True,
                    job_id=job_id,
                    message="Thumbnail generated",
                    output_path=encoded,
                    file_size=len(data)
                )
            else:
                output_dest = output.get("path", f"thumbnails/{job_id}.{output_ext}")
                await self.storage.upload(output_path, output_dest, f"image/{output_ext}")
                return JobResult(
                    success=True,
                    job_id=job_id,
                    message="Thumbnail generated",
                    output_path=output_dest,
                    file_size=os.path.getsize(output_path)
                )
                
        except Exception as e:
            logger.exception(f"Thumbnail job failed: {job_id}")
            return JobResult(
                success=False,
                job_id=job_id,
                message="Thumbnail generation failed",
                error=str(e)
            )
        finally:
            for path in [temp_input, temp_output]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

    async def process_convert(self, job_data: JobData) -> JobResult:
        job_id = job_data.job_id or str(uuid.uuid4())
        
        temp_input = None
        temp_output = None
        
        try:
            source = job_data.source
            output = job_data.output
            options = job_data.options
            
            # Build conversion options
            convert_options = ConversionOptions(
                output_format=options.get("output_format", "pdf"),
                quality=options.get("quality", 85),
                width=options.get("width"),
                height=options.get("height"),
                page=options.get("page", 1)
            )
            
            # Download input
            if source["type"] == "upload":
                import base64
                file_bytes = base64.b64decode(source.get("data", ""))
                temp_input = f"/tmp/conversions/{job_id}_input"
                async with aiofiles.open(temp_input, 'wb') as f:
                    await f.write(file_bytes)
            else:
                temp_input = f"/tmp/conversions/{job_id}_input"
                await self.storage.download(source["path"], temp_input)
            
            # Convert
            output_ext = convert_options.output_format
            temp_output = f"/tmp/conversions/converted_{job_id}.{output_ext}"
            
            output_path = await self.converter_service.convert(
                temp_input, temp_output, convert_options
            )
            
            # Upload output
            if output["type"] == "stream":
                async with aiofiles.open(output_path, 'rb') as f:
                    data = await f.read()
                import base64
                encoded = base64.b64encode(data).decode('utf-8')
                return JobResult(
                    success=True,
                    job_id=job_id,
                    message=f"Converted to {output_ext}",
                    output_path=encoded,
                    file_size=len(data)
                )
            else:
                output_dest = output.get("path", f"converted/{job_id}.{output_ext}")
                content_type = "application/pdf" if output_ext == "pdf" else f"image/{output_ext}"
                await self.storage.upload(output_path, output_dest, content_type)
                return JobResult(
                    success=True,
                    job_id=job_id,
                    message=f"Converted to {output_ext}",
                    output_path=output_dest,
                    file_size=os.path.getsize(output_path)
                )
                
        except Exception as e:
            logger.exception(f"Convert job failed: {job_id}")
            return JobResult(
                success=False,
                job_id=job_id,
                message="Conversion failed",
                error=str(e)
            )
        finally:
            for path in [temp_input, temp_output]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

    async def process(self, job_data: JobData) -> JobResult:
        logger.info(f"Processing job: {job_data.job_type} - {job_data.job_id}")
        
        if job_data.job_type == "thumbnail":
            result = await self.process_thumbnail(job_data)
        elif job_data.job_type == "convert":
            result = await self.process_convert(job_data)
        else:
            result = JobResult(
                success=False,
                job_id=job_data.job_id or "unknown",
                message=f"Unknown job type: {job_data.job_type}",
                error="Unknown job type"
            )
        
        # Send webhook if configured
        if job_data.webhook_url:
            await self._send_webhook(job_data.webhook_url, result)
        
        return result

    async def _send_webhook(self, url: str, result: JobResult):
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=result.to_dict())
        except Exception as e:
            logger.warning(f"Webhook failed: {e}")