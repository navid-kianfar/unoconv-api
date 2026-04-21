from typing import Optional, Literal
from pydantic import BaseModel, Field


class ThumbnailOptions(BaseModel):
    width: int = Field(default=300, ge=50, le=2000, description="Output width in pixels")
    height: int = Field(default=300, ge=50, le=2000, description="Output height in pixels")
    quality: int = Field(default=85, ge=1, le=100, description="JPEG quality (1-100)")
    trim: bool = Field(default=False, description="Trim whitespace from image")
    type: Literal["thumbnail", "firstpage"] = Field(default="thumbnail")
    output_format: Literal["png", "jpg", "gif"] = Field(default="png")


class SourceUpload(BaseModel):
    file: bytes = Field(description="File bytes (multipart form key: 'file')")


class SourceFile(BaseModel):
    type: Literal["file"] = "file"
    path: str = Field(description="Local file path")


class SourceS3(BaseModel):
    type: Literal["s3"] = "s3"
    path: str = Field(description="S3 path: s3://bucket/key or bucket/key")


class Source(BaseModel):
    type: Literal["upload", "file", "s3"]
    path: Optional[str] = Field(None, description="File path or S3 path (not used for upload)")


class OutputStream(BaseModel):
    type: Literal["stream"] = "stream"


class OutputFile(BaseModel):
    type: Literal["file"] = "file"
    path: str = Field(description="Local file path")


class OutputS3(BaseModel):
    type: Literal["s3"] = "s3"
    path: str = Field(description="S3 path: s3://bucket/key or bucket/key")


class Output(BaseModel):
    type: Literal["stream", "file", "s3"]
    path: Optional[str] = Field(None, description="Output path (required for file/s3 types)")


class ThumbnailRequest(BaseModel):
    source: Source = Field(description="Input source definition")
    output: Output = Field(description="Output destination definition")
    options: Optional[ThumbnailOptions] = Field(default_factory=ThumbnailOptions)


class ThumbnailResponse(BaseModel):
    success: bool
    message: str
    output_path: Optional[str] = Field(None, description="Output path for file/s3 types")
    file_size: Optional[int] = None
    file_type: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    supported_formats: dict