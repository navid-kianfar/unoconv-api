# unoconv-api

A REST API for generating thumbnails and converting files between formats using LibreOffice (unoconv). Supports multiple input/output sources including local files, S3, and FTP storage.

**Features:**
- Generate thumbnails from images, videos, and documents
- Convert files between formats (DOCX→PDF, XLSX→PDF, etc.)
- Input/Output from local files, S3, FTP, or direct upload
- Docker multi-arch support (amd64 & arm64)
- Background worker with RabbitMQ queue support

## Quick Start

```bash
# Docker
cd api && docker-compose up -d

# Or Python
cd api && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

---

## Authentication

All endpoints require `X-API-KEY` header:

```bash
curl -X POST "http://localhost:8000/api/v1/thumbnail" \
  -H "X-API-KEY: your-api-key" \
  ...
```

Set API key via environment:
```bash
API_KEY=your-secure-api-key
```

If `API_KEY` is not set, authentication is bypassed (for development).

---

## Common Parameters

| Parameter | Description |
|-----------|-------------|
| `source_type` | Input source: `upload`, `file`, `local`, `s3`, `ftp`, `sftp`, `remote` |
| `source_path` | Path to input file |
| `output_type` | Output destination: `stream`, `file`, `local`, `s3`, `ftp`, `sftp`, `remote` |
| `output_path` | Output path |
| `file` | Multipart file (for upload) |

### Storage Backends

| Backend | Path Format | Description |
|--------|------------|-------------|
| `local` | `/path/to/file` | Local filesystem |
| `s3` | `s3://bucket/key` | AWS S3 or compatible |
| `ftp` | `ftp://host/path` | FTP server |
| `sftp` | `sftp://host/path` | SFTP/SSH server |
| `remote` | `https://url/path` | Remote HTTP/HTTPS URL |

### Storage Credentials (optional)

| Parameter | Description |
|-----------|-------------|
| `s3_endpoint_url` | S3 endpoint URL |
| `s3_access_key` | S3 access key |
| `s3_secret_key` | S3 secret key |
| `s3_region` | S3 region |
| `ftp_host` | FTP host |
| `ftp_port` | FTP port (default: 21) |
| `ftp_username` | FTP username |
| `ftp_password` | FTP password |
| `sftp_host` | SFTP host |
| `sftp_port` | SFTP port (default: 22) |
| `sftp_username` | SFTP username |
| `sftp_password` | SFTP password |
| `sftp_key_path` | SFTP private key path |
| `remote_auth_username` | Remote URL auth username |
| `remote_auth_password` | Remote URL auth password |

Credentials passed in request override environment variables.

---

## Generate Thumbnail

```
POST /api/v1/thumbnail
```

### Thumbnail Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_format` | `png` | Output format: `png`, `jpg`, `gif` |
| `width` | 300 | Output width in pixels |
| `height` | 300 | Output height in pixels |
| `quality` | 85 | JPEG quality (1-100) |
| `trim` | false | Trim whitespace |
| `type` | thumbnail | `thumbnail` or `firstpage` |
| `page` | 1 | Page number for documents |
| `frame` | auto | Frame number for videos (default: middle) |

### Examples

**S3 input → S3 output:**
```bash
curl -X POST "http://localhost:8000/api/v1/thumbnail" \
  -H "X-API-KEY: your-key" \
  -F "source_type=s3" \
  -F "source_path=bucket/docs/report.pdf" \
  -F "output_type=s3" \
  -F "output_path=bucket/thumbs/report.png" \
  -F "width=300" -F "height=300"
```

**Upload → Stream download:**
```bash
curl -X POST "http://localhost:8000/api/v1/thumbnail" \
  -H "X-API-KEY: your-key" \
  -F "source_type=upload" \
  -F "file=@document.pdf" \
  -F "output_type=stream" \
  -o thumbnail.png
```

**Video with specific frame:**
```bash
curl -X POST "http://localhost:8000/api/v1/thumbnail" \
  -H "X-API-KEY: your-key" \
  -F "source_type=s3" \
  -F "source_path=bucket/videos/movie.mp4" \
  -F "output_type=stream" \
  -F "frame=100" \
  -o thumbnail.png
```

**Document specific page:**
```bash
curl -X POST "http://localhost:8000/api/v1/thumbnail" \
  -H "X-API-KEY: your-key" \
  -F "source_type=file" \
  -F "source_path=/data/doc.pdf" \
  -F "output_type=stream" \
  -F "page=5" \
  -o page5.png
```

**Remote URL to S3:**
```bash
curl -X POST "http://localhost:8000/api/v1/thumbnail" \
  -H "X-API-KEY: your-key" \
  -F "source_type=remote" \
  -F "source_path=https://example.com/document.pdf" \
  -F "output_type=s3" \
  -F "output_path=s3://bucket/thumbs/doc.png"
```

---

## Convert File

```
POST /api/v1/convert
```

### Convert Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_format` | (required) | Target format: `pdf`, `png`, `jpg`, `docx`, `xlsx`, etc. |
| `page` | 1 | Page number for multi-page inputs |
| `quality` | 85 | Output quality (1-100) |
| `width` | - | Resize width (optional) |
| `height` | - | Resize height (optional) |

### Supported Conversions

| From | To |
|------|-----|
| DOCX, DOC, DOCM, ODT, RTF, TXT, XML, HTML | PDF |
| XLSX, XLS, XLSM, ODS | PDF |
| PPTX, PPT, ODP | PDF |
| PDF | PNG, JPG |
| PNG, JPG, GIF, BMP, TIFF, WebP | PNG, JPG, PDF |

### Examples

**DOCX → PDF (S3 to S3):**
```bash
curl -X POST "http://localhost:8000/api/v1/convert" \
  -H "X-API-KEY: your-key" \
  -F "source_type=s3" \
  -F "source_path=bucket/docs/report.docx" \
  -F "output_type=s3" \
  -F "output_path=bucket/converted/report.pdf" \
  -F "output_format=pdf"
```

**Upload → S3:**
```bash
curl -X POST "http://localhost:8000/api/v1/convert" \
  -H "X-API-KEY: your-key" \
  -F "source_type=upload" \
  -F "file=@spreadsheet.xlsx" \
  -F "output_type=s3" \
  -F "output_path=bucket/output/spreadsheet.pdf" \
  -F "output_format=pdf"
```

**FTP to Stream:**
```bash
curl -X POST "http://localhost:8000/api/v1/convert" \
  -H "X-API-KEY: your-key" \
  -F "source_type=ftp" \
  -F "source_path=ftp.example.com/docs/file.docx" \
  -F "output_type=stream" \
  -F "output_format=pdf" \
  -o file.pdf
```

---

## Input/Output Matrix

| source_type | output_type | Use Case |
|-------------|-------------|----------|
| upload | stream | Browser upload → download |
| upload | file | Upload → save locally |
| upload | s3 | Upload → save to S3 |
| upload | ftp | Upload → save to FTP |
| file | stream | Local file → download |
| file | file | Local file → local output |
| file | s3 | Local file → S3 |
| file | ftp | Local file → FTP |
| s3 | stream | S3 → download |
| s3 | file | S3 → local |
| s3 | s3 | S3 → S3 |
| s3 | ftp | S3 → FTP |
| ftp | stream | FTP → download |
| ftp | file | FTP → local |
| ftp | s3 | FTP → S3 |
| ftp | ftp | FTP → FTP |

---

## Python Examples

### Thumbnail
```python
import requests

headers = {"X-API-KEY": "your-key"}

# S3 → S3 with credentials
resp = requests.post("http://localhost:8000/api/v1/thumbnail", 
    headers=headers,
    data={
        "source_type": "s3",
        "source_path": "bucket/input.pdf",
        "output_type": "s3",
        "output_path": "bucket/output/thumb.png",
        "width": 300,
        "height": 300,
    })
```

### Convert
```python
import requests

headers = {"X-API-KEY": "your-key"}

# Convert DOCX to PDF
resp = requests.post("http://localhost:8000/api/v1/convert",
    headers=headers,
    data={
        "source_type": "file",
        "source_path": "/data/doc.docx",
        "output_type": "stream",
        "output_format": "pdf"
    })

with open("output.pdf", "wb") as f:
    f.write(resp.content)
```

---

## Environment Variables

```bash
# Authentication
API_KEY=your-secure-api-key

# Temp directories
TEMP_DIR=/tmp/thumbnails

# S3 (optional)
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=your-key
S3_SECRET_KEY=your-secret
S3_REGION=us-east-1
S3_BUCKET=default-bucket

# FTP (optional)
FTP_HOST=ftp.example.com
FTP_PORT=21
FTP_USERNAME=user
FTP_PASSWORD=pass
```

---

## Docker Multi-Arch Build

```bash
docker buildx create --name mybuilder --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t thumbnail-api:latest --push .
```

---

## Background Worker

The API supports async processing via a RabbitMQ worker.

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Client    │────▶│  RabbitMQ    │────▶│   Worker Node   │
│  (Submit)   │     │   Queue      │     │  (Process Job)  │
└─────────────┘     └──────────────┘     └─────────────────┘
```

### Run with Docker Compose

```bash
# Start API + Worker + RabbitMQ
docker-compose -f docker-compose.worker.yml up -d

# Or just start worker
docker-compose -f docker-compose.worker.yml up -d unoconv-worker
```

### Environment Variables (Worker)

| Variable | Default | Description |
|----------|---------|-------------|
| `RABBITMQ_URL` | amqp://localhost:5672 | RabbitMQ connection |
| `QUEUE_NAME` | unoconv-jobs | Job queue name |
| `MAX_CONCURRENT` | 2 | Max parallel jobs |
| `JOB_TIMEOUT` | 300 | Job timeout (seconds) |

### Submit Jobs via Client

```python
from worker import QueueClient
import asyncio

async def submit():
    client = QueueClient(rabbitmq_url="amqp://localhost:5672")
    
    # Submit thumbnail job
    await client.submit_thumbnail(
        source={"type": "s3", "path": "bucket/docs/file.pdf"},
        output={"type": "s3", "path": "bucket/thumbs/out.png"},
        options={"width": 300, "height": 300},
        webhook_url="https://myapp.com/webhook"  # optional
    )
    
    # Submit conversion job
    await client.submit_convert(
        source={"type": "file", "path": "/data/doc.docx"},
        output={"type": "stream"},
        options={"output_format": "pdf"}
    )
    
    await client.disconnect()

asyncio.run(submit())
```

### CLI Client

```bash
# Submit thumbnail job
python -m worker.client \
  --type thumbnail \
  --source-type s3 \
  --source-path bucket/input.pdf \
  --output-type s3 \
  --output-path bucket/thumbnails/out.png

# Submit convert job
python -m worker.client \
  --type convert \
  --source-type file \
  --source-path /data/doc.docx \
  --output-type stream \
  --output-format pdf
```

### Job Webhook

When a job completes, the worker can send a webhook notification:

```json
{
  "success": true,
  "job_id": "uuid-here",
  "message": "Thumbnail generated",
  "output_path": "s3://bucket/thumbnails/out.png",
  "file_size": 24567
}
```

---

## License

MIT