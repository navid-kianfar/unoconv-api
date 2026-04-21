import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional
from enum import Enum


class ConversionType(str, Enum):
    DOCUMENT_TO_PDF = "document_to_pdf"
    PDF_TO_IMAGE = "pdf_to_image"
    IMAGE_TO_IMAGE = "image_to_image"
    IMAGE_TO_PDF = "image_to_pdf"
    VIDEO_TO_FRAMES = "video_to_frames"


class ConversionOptions:
    def __init__(
        self,
        output_format: str,
        quality: int = 85,
        width: Optional[int] = None,
        height: Optional[int] = None,
        page: int = 1,
    ):
        self.output_format = output_format.lower().replace('.', '')
        self.quality = quality
        self.width = width
        self.height = height
        self.page = page


class ConverterService:
    # All supported conversions via unoconv (LibreOffice)
    # Format: (input_ext, output_ext) -> ConversionType
    CONVERSION_MATRIX = {
        # Documents to PDF
        ('docx', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('doc', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('docm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('dotx', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('dotm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('odt', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('ott', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('oth', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('odm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('rtf', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('txt', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('csv', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('xml', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('html', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('htm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        
        # Spreadsheets to PDF
        ('xlsx', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('xls', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('xlsm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('xltx', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('xltm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('xlsb', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('ods', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('ots', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('dbf', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        
        # Presentations to PDF
        ('pptx', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('ppt', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('pptm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('ppsx', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('ppsm', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('odp', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('otp', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        
        # macOS/iWork to PDF
        ('pages', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('numbers', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        ('key', 'pdf'): ConversionType.DOCUMENT_TO_PDF,
        
        # PDF to Images
        ('pdf', 'png'): ConversionType.PDF_TO_IMAGE,
        ('pdf', 'jpg'): ConversionType.PDF_TO_IMAGE,
        ('pdf', 'jpeg'): ConversionType.PDF_TO_IMAGE,
        
        # Images to Images
        ('jpg', 'png'): ConversionType.IMAGE_TO_IMAGE,
        ('jpeg', 'png'): ConversionType.IMAGE_TO_IMAGE,
        ('png', 'jpg'): ConversionType.IMAGE_TO_IMAGE,
        ('gif', 'png'): ConversionType.IMAGE_TO_IMAGE,
        ('bmp', 'png'): ConversionType.IMAGE_TO_IMAGE,
        ('tiff', 'png'): ConversionType.IMAGE_TO_IMAGE,
        ('tif', 'png'): ConversionType.IMAGE_TO_IMAGE,
        ('webp', 'png'): ConversionType.IMAGE_TO_IMAGE,
        ('png', 'jpg'): ConversionType.IMAGE_TO_IMAGE,
        ('jpg', 'gif'): ConversionType.IMAGE_TO_IMAGE,
        ('gif', 'jpg'): ConversionType.IMAGE_TO_IMAGE,
        
        # Images to PDF
        ('jpg', 'pdf'): ConversionType.IMAGE_TO_PDF,
        ('jpeg', 'pdf'): ConversionType.IMAGE_TO_PDF,
        ('png', 'pdf'): ConversionType.IMAGE_TO_PDF,
        ('gif', 'pdf'): ConversionType.IMAGE_TO_PDF,
        ('bmp', 'pdf'): ConversionType.IMAGE_TO_PDF,
        ('tiff', 'pdf'): ConversionType.IMAGE_TO_PDF,
        ('tif', 'pdf'): ConversionType.IMAGE_TO_PDF,
    }

    def __init__(self, temp_dir: str = "/tmp/conversions"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

    def get_conversion_type(self, input_path: str, output_format: str) -> ConversionType:
        input_ext = Path(input_path).suffix.lower().replace('.', '')
        
        conversion_type = self.CONVERSION_MATRIX.get((input_ext, output_format))
        
        if not conversion_type:
            supported = ", ".join([f"{inp}→{out}" for (inp, out), _ in self.CONVERSION_MATRIX.items()])
            raise ValueError(
                f"Conversion from {input_ext} to {output_format} is not supported. "
                f"Supported: {supported}"
            )
        
        return conversion_type

    def _build_document_to_pdf_command(self, input_path: str, output_path: str, options: ConversionOptions) -> str:
        ext = Path(input_path).suffix.lower().replace('.', '')
        
        if ext == 'txt' or ext == 'csv':
            return f'enscript -q -B -p - "{input_path}" | ps2pdf - "{output_path}"'
        
        page_spec = f"-e PageRange={options.page}" if options.page > 1 else ""
        cmd = f'unoconv -f pdf {page_spec} -o "{output_path}" "{input_path}"'
        return cmd

    def _build_pdf_to_image_command(self, input_path: str, output_path: str, options: ConversionOptions) -> str:
        density = '150'
        resize = ''
        if options.width and options.height:
            resize = f'-resize {options.width}x{options.height}'
        
        cmd = f'convert -density {density} -quality {options.quality} {resize} "{input_path}[{options.page - 1}]" "{output_path}"'
        return cmd

    def _build_image_to_image_command(self, input_path: str, output_path: str, options: ConversionOptions) -> str:
        resize = ''
        if options.width and options.height:
            resize = f'-resize {options.width}x{options.height}'
        
        cmd = f'convert -quality {options.quality} {resize} "{input_path}" "{output_path}"'
        return cmd

    def _build_image_to_pdf_command(self, input_path: str, output_path: str) -> str:
        cmd = f'convert "{input_path}" "{output_path}"'
        return cmd

    async def convert(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        options: Optional[ConversionOptions] = None
    ) -> str:
        if options is None:
            raise ValueError("ConversionOptions is required")
        
        if output_path is None:
            output_path = os.path.join(self.temp_dir, f"converted_{uuid.uuid4()}.{options.output_format}")
        
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        conversion_type = self.get_conversion_type(input_path, options.output_format)
        
        if conversion_type == ConversionType.DOCUMENT_TO_PDF:
            cmd = self._build_document_to_pdf_command(input_path, output_path, options)
        elif conversion_type == ConversionType.PDF_TO_IMAGE:
            cmd = self._build_pdf_to_image_command(input_path, output_path, options)
        elif conversion_type == ConversionType.IMAGE_TO_IMAGE:
            cmd = self._build_image_to_image_command(input_path, output_path, options)
        elif conversion_type == ConversionType.IMAGE_TO_PDF:
            cmd = self._build_image_to_pdf_command(input_path, output_path)
        else:
            raise ValueError(f"Unsupported conversion type: {conversion_type}")
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
            raise RuntimeError(f"Conversion failed: {error_msg}")
        
        if not os.path.exists(output_path):
            raise RuntimeError(f"Output file was not created: {output_path}")
        
        return output_path