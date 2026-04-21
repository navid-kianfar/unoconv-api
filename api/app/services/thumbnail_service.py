import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from enum import Enum
import aiofiles


class ThumbnailType(str, Enum):
    THUMBNAIL = "thumbnail"
    FIRSTPAGE = "firstpage"


class OutputFormat(str, Enum):
    PNG = "png"
    JPG = "jpg"
    GIF = "gif"


class ThumbnailOptions:
    def __init__(
        self,
        width: int = 300,
        height: int = 300,
        quality: int = 85,
        trim: bool = False,
        type: ThumbnailType = ThumbnailType.THUMBNAIL,
        output_format: OutputFormat = OutputFormat.PNG,
        page: int = 1,
        frame: Optional[int] = None,
    ):
        self.width = width
        self.height = height
        self.quality = quality
        self.trim = trim
        self.type = type
        self.output_format = output_format
        self.page = page
        self.frame = frame


class ThumbnailService:
    IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'svg', 'ico', 'jfif']
    VIDEO_EXTS = ['mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'webm', 'mpeg', 'mpg', 'm4v', '3gp', 'ogv']
    DOC_EXTS = [
        'doc', 'docx', 'docm', 'dotx', 'dotm',
        'odt', 'ott', 'oth', 'odm',
        'rtf', 'txt', 'csv',
        'xls', 'xlsx', 'xlsm', 'xltx', 'xltm', 'ods', 'ots',
        'ppt', 'pptx', 'pptm', 'ppsx', 'ppsm', 'odp', 'otp',
        'pdf', 'pages', 'numbers', 'key'
    ]

    def __init__(self, temp_dir: str = "/tmp/thumbnails"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

    def _get_file_type(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower().replace('.', '')
        
        if ext in self.IMAGE_EXTS:
            return 'image'
        elif ext in self.VIDEO_EXTS:
            return 'video'
        elif ext in self.DOC_EXTS:
            return 'document'
        
        return 'unknown'

    def _build_image_command(self, input_path: str, output_path: str, options: ThumbnailOptions) -> str:
        trim_flag = '-trim' if options.trim else ''
        
        if options.type == ThumbnailType.THUMBNAIL:
            geometry = f'-geometry {options.height} -extent {options.width}x{options.height}'
        else:
            geometry = ''
        
        cmd = f'convert {trim_flag} -quality {options.quality} {geometry} -colorspace RGB "{input_path}" "{output_path}"'
        return cmd

    def _build_video_command(self, input_path: str, output_path: str, options: ThumbnailOptions) -> str:
        if options.frame is not None:
            frame_select = f'select=eq(n\\,{options.frame})'
        else:
            frame_select = 'select=eq(n\\,floor(tb/2))'
        
        cmd = f'ffmpeg -y -i "{input_path}" -vf "[v]fps=1,{frame_select}[out]" -frames:v 1 "{output_path}"'
        return cmd

    def _build_document_command(self, input_path: str, output_path: str, options: ThumbnailOptions) -> str:
        tmp_pdf = os.path.join(self.temp_dir, f"{uuid.uuid4()}.pdf")
        ext = Path(input_path).suffix.lower().replace('.', '')
        
        if ext == 'pdf':
            pdf_input = input_path
        else:
            unoconv_cmd = f'unoconv -e PageRange={options.page} -o "{tmp_pdf}" "{input_path}"'
            pdf_input = f'"{tmp_pdf}"'
            cmd = f'{unoconv_cmd} && convert -density 150 -quality {options.quality} -geometry {options.height} -extent {options.width}x{options.height} {pdf_input}[0] "{output_path}" && rm -f "{tmp_pdf}"'
            return cmd
        
        if options.type == ThumbnailType.THUMBNAIL:
            return f'convert -density 150 -quality {options.quality} -geometry {options.height} -extent {options.width}x{options.height} {pdf_input}[{options.page - 1}] "{output_path}"'
        else:
            return f'convert -quality {options.quality} {pdf_input}[{options.page - 1}] "{output_path}"'

    async def generate(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        options: Optional[ThumbnailOptions] = None
    ) -> str:
        if options is None:
            options = ThumbnailOptions()
        
        if output_path is None:
            output_filename = f"{uuid.uuid4()}.{options.output_format.value}"
            output_path = os.path.join(self.temp_dir, output_filename)
        
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        file_type = self._get_file_type(input_path)
        
        if file_type == 'unknown':
            raise ValueError(f"Unsupported file type: {input_path}")
        
        if file_type == 'video':
            cmd = self._build_video_command(input_path, output_path, options)
        elif file_type == 'image':
            cmd = self._build_image_command(input_path, output_path, options)
        elif file_type == 'document':
            cmd = self._build_document_command(input_path, output_path, options)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
            raise RuntimeError(f"Thumbnail generation failed: {error_msg}")
        
        if not os.path.exists(output_path):
            raise RuntimeError(f"Output file was not created: {output_path}")
        
        return output_path

    async def generate_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        options: Optional[ThumbnailOptions] = None
    ) -> bytes:
        input_path = os.path.join(self.temp_dir, f"{uuid.uuid4()}_{filename}")
        
        async with aiofiles.open(input_path, 'wb') as f:
            await f.write(file_bytes)
        
        try:
            output_path = await self.generate(input_path, options=options)
            
            async with aiofiles.open(output_path, 'rb') as f:
                result_bytes = await f.read()
            
            return result_bytes
        finally:
            self._cleanup([input_path])

    async def copy_file(self, src: str, dst: str):
        import shutil
        os.makedirs(os.path.dirname(dst) or '.', exist_ok=True)
        shutil.copy2(src, dst)

    def _cleanup(self, paths: list):
        for path in paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass