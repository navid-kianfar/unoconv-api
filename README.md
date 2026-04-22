# unoconv-api

A REST API for generating thumbnails and converting files between formats using LibreOffice and ImageMagick. Supports multiple storage backends including local files, S3, FTP, SFTP, and remote URLs.

**Features:**
- Generate thumbnails from images, videos, PDFs, and documents
- Convert files between formats dynamically (LibreOffice + ImageMagick)
- Multiple storage backends: local, S3, FTP, SFTP, remote URLs
- Docker multi-arch support (amd64 & arm64)
- Background worker with RabbitMQ queue support
- API key authentication (Global Swagger Authorization)

## Quick Start

```bash
# Clone and run with Docker
docker run -d -p 8000:8000 -e API_KEY=your-key -v /data:/data unoconv-api:latest

# Or use Docker Compose
cd api && cp .env.example .env && docker-compose up -d
```

API docs: http://localhost:8000/

---

## Authentication

All endpoints require `X-API-KEY` header. In Swagger UI, use the **"Authorize"** button at the top to set your key once for all requests.

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
| `source_type` | Input source: `stream`, `local`, `s3`, `ftp`, `sftp`, `remote` |
| `source_path` | Path to input file (required for all except `stream`) |
| `output_type` | Output destination: `stream`, `local`, `s3`, `ftp`, `sftp`, `remote` |
| `output_path` | Output path (required for all except `stream`) |
| `file` | Multipart file upload (required when `source_type` is `stream`) |

### Storage Backends

| Backend | Path Format | Description |
|--------|------------|-------------|
| `stream` | (Multipart File) | Direct upload/download in the request/response |
| `local` | `/path/to/file` | Local filesystem on the server machine |
| `s3` | `s3://bucket/key` | AWS S3 or compatible |
| `ftp` | `ftp://host/path` | FTP server |
| `sftp` | `sftp://host/path` | SFTP/SSH server |
| `remote` | `https://url/path` | Remote HTTP/HTTPS URL (source only) |

### Storage Credentials (optional)

Credentials can be passed in the request body to override environment variables:
`s3_endpoint_url`, `s3_access_key`, `s3_secret_key`, `s3_region`, `ftp_host`, `ftp_port`, `ftp_username`, `ftp_password`, `sftp_host`, `sftp_port`, `sftp_username`, `sftp_password`, `sftp_key_path`.

---

## Generate Thumbnail

```
POST /api/v1/thumbnail
```

### Thumbnail Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `output_format` | `png` | Dropdown: `png`, `jpg`, `gif` |
| `width` | 300 | Output width in pixels |
| `height` | 300 | Output height in pixels |
| `quality` | 85 | JPEG quality (1-100) |
| `trim` | false | Trim whitespace |
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
  -F "output_path=bucket/thumbs/report.png"
```

**Upload → Stream download:**
```bash
curl -X POST "http://localhost:8000/api/v1/thumbnail" \
  -H "X-API-KEY: your-key" \
  -F "source_type=stream" \
  -F "file=@document.pdf" \
  -F "output_type=stream" \
  -o thumbnail.png
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
| `source_type` | `stream` | `stream`, `local`, `s3`, etc. |
| `output_type` | `stream` | `stream`, `local`, `s3`, etc. |

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

### Submit Jobs via Python

```python
from worker import QueueClient
import asyncio

async def submit():
    client = QueueClient(rabbitmq_url="amqp://localhost:5672")
    
    # Submit thumbnail job
    await client.submit_thumbnail(
        source={"type": "local", "path": "/data/input.pdf"},
        output={"type": "local", "path": "/data/thumbnails/out.png"},
        options={"width": 300, "height": 300},
        webhook_url="https://myapp.com/webhook"
    )
    
    await client.disconnect()

asyncio.run(submit())
```

### CLI Client

```bash
# Submit thumbnail job (local to local)
python -m worker.client \
  --type thumbnail \
  --source-type local \
  --source-path /data/input.pdf \
  --output-type local \
  --output-path /data/thumbnails/out.png

# Submit convert job (S3 to S3)
python -m worker.client \
  --type convert \
  --source-type s3 \
  --source-path bucket/doc.docx \
  --output-type s3 \
  --output-path bucket/pdf/doc.pdf \
  --output-format pdf
```

### Job Webhook

When a job completes, the worker can send a JSON payload to the `webhook_url`:

```json
{
  "success": true,
  "job_id": "uuid-here",
  "message": "Thumbnail generated",
  "output_path": "local:/data/thumbnails/out.png",
  "file_size": 24567
}
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `API_KEY` | Your secure API key |
| `TEMP_DIR` | Directory for temporary files |
| `S3_ENDPOINT_URL` | S3 endpoint URL (optional) |
| `S3_ACCESS_KEY` | S3 access key (optional) |
| `S3_SECRET_KEY` | S3 secret key (optional) |
| `S3_REGION` | S3 region (optional) |

---

## License

MIT