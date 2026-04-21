import os
import uuid
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class JobType(str, Enum):
    THUMBNAIL = "thumbnail"
    CONVERT = "convert"


@dataclass
class JobData:
    job_type: JobType
    source: dict
    output: dict
    options: dict = field(default_factory=dict)
    job_id: Optional[str] = None
    webhook_url: Optional[str] = None

    def to_dict(self):
        return {
            "job_type": self.job_type.value,
            "source": self.source,
            "output": self.output,
            "options": self.options,
            "job_id": self.job_id,
            "webhook_url": self.webhook_url
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            job_type=JobType(data["job_type"]),
            source=data["source"],
            output=data["output"],
            options=data.get("options", {}),
            job_id=data.get("job_id"),
            webhook_url=data.get("webhook_url")
        )


@dataclass
class JobResult:
    success: bool
    job_id: str
    message: str = ""
    output_path: Optional[str] = None
    file_size: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self):
        return {
            "success": self.success,
            "job_id": self.job_id,
            "message": self.message,
            "output_path": self.output_path,
            "file_size": self.file_size,
            "error": self.error
        }


class QueueConfig:
    def __init__(
        self,
        redis_url: Optional[str] = None,
        rabbitmq_url: Optional[str] = None,
        queue_name: str = "unoconv-jobs",
        max_concurrent: int = 2,
        job_timeout: int = 300
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://localhost:5672")
        self.queue_name = queue_name
        self.max_concurrent = max_concurrent
        self.job_timeout = job_timeout