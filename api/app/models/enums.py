from enum import Enum

class SourceType(str, Enum):
    STREAM = "stream"
    LOCAL = "local"
    S3 = "s3"
    FTP = "ftp"
    SFTP = "sftp"
    REMOTE = "remote"

class OutputType(str, Enum):
    STREAM = "stream"
    LOCAL = "local"
    S3 = "s3"
    FTP = "ftp"
    SFTP = "sftp"
    REMOTE = "remote"

class ThumbnailFormat(str, Enum):
    PNG = "png"
    JPG = "jpg"
    GIF = "gif"

class ConversionFormat(str, Enum):
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    GIF = "gif"
    DOCX = "docx"
    DOC = "doc"
    XLSX = "xlsx"
    XLS = "xls"
    PPTX = "pptx"
    PPT = "ppt"
    ODT = "odt"
    ODS = "ods"
    ODP = "odp"
    HTML = "html"
    TXT = "txt"
    CSV = "csv"
