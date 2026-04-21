import os
import uuid
import asyncio
from pathlib import Path
from typing import Optional


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
    def __init__(self, temp_dir: str = "/tmp/conversions"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)

    def _get_libreoffice_format(self, ext: str) -> Optional[str]:
        ext = ext.lower().replace('.', '')
        format_map = {
            'pdf': 'pdf',
            'doc': 'doc',
            'docx': 'docx',
            'odt': 'odt',
            'rtf': 'rtf',
            'txt': 'txt',
            'html': 'html',
            'htm': 'html',
            'xls': 'xls',
            'xlsx': 'xlsx',
            'ods': 'ods',
            'csv': 'csv',
            'ppt': 'ppt',
            'pptx': 'pptx',
            'odp': 'odp',
            'png': 'png',
            'jpg': 'jpg',
            'jpeg': 'jpg',
            'gif': 'gif',
            'bmp': 'bmp',
            'tiff': 'tiff',
            'tif': 'tiff',
            'webp': 'webp',
        }
        return format_map.get(ext)

    def _is_document_format(self, ext: str) -> bool:
        ext = ext.lower().replace('.', '')
        doc_formats = {
            'doc', 'docx', 'docm', 'dotx', 'dotm',
            'odt', 'ott', 'oth', 'odm',
            'rtf', 'txt', 'csv', 'xml',
            'html', 'htm',
            'xlsx', 'xls', 'xlsm', 'xltx', 'xltm', 'xlsb', 'ods', 'ots', 'dbf',
            'pptx', 'ppt', 'pptm', 'ppsx', 'ppsm', 'odp', 'otp',
            'pages', 'numbers', 'key',
            'pdf'
        }
        return ext in doc_formats

    def _is_image_format(self, ext: str) -> bool:
        ext = ext.lower().replace('.', '')
        image_formats = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp'}
        return ext in image_formats

    def _build_libreoffice_command(self, input_path: str, output_path: str, output_format: str) -> str:
        lo_format = self._get_libreoffice_format(output_format)
        if not lo_format:
            return None
        cmd = f'libreoffice --headless --convert-to {lo_format} --outdir "$(dirname "{output_path}")" "{input_path}"'
        return cmd

    def _build_imagemagick_command(self, input_path: str, output_path: str, options: ConversionOptions) -> str:
        ext = Path(input_path).suffix.lower().replace('.', '')
        
        if ext == 'pdf':
            density = '150'
            resize = ''
            if options.width and options.height:
                resize = f'-resize {options.width}x{options.height}'
            return f'convert -density {density} -quality {options.quality} {resize} "{input_path}[{options.page - 1}]" "{output_path}"'
        
        if options.output_format in ['pdf']:
            return f'convert "{input_path}" "{output_path}"'
        
        resize = ''
        if options.width and options.height:
            resize = f'-resize {options.width}x{options.height}'
        
        return f'convert -quality {options.quality} {resize} "{input_path}" "{output_path}"'

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
        
        input_ext = Path(input_path).suffix.lower().replace('.', '')
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        output_created = False
        error_messages = []
        
        if self._is_document_format(input_ext):
            cmd = self._build_libreoffice_command(input_path, output_path, options.output_format)
            if cmd:
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and os.path.exists(output_path):
                    output_created = True
                else:
                    error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
                    error_messages.append(f"LibreOffice: {error_msg}")
                    
                    if not output_created and options.output_format in ['png', 'jpg', 'jpeg']:
                        alt_output = os.path.join(
                            os.path.dirname(output_path),
                            f"{Path(input_path).stem}.{options.output_format}"
                        )
                        if os.path.exists(alt_output):
                            os.rename(alt_output, output_path)
                            output_created = True
        
        if not output_created and self._is_image_format(input_ext):
            cmd = self._build_imagemagick_command(input_path, output_path, options)
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                output_created = True
            else:
                error_msg = stderr.decode() if stderr else stdout.decode() if stdout else "Unknown error"
                error_messages.append(f"ImageMagick: {error_msg}")
        
        if not output_created:
            raise RuntimeError(
                f"Conversion failed. Attempted methods:\n" + "\n".join(error_messages)
            )
        
        return output_path
