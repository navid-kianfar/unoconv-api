import os
import asyncio
import logging
import signal
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.services.storage_service import get_storage_service
from app.services.thumbnail_service import ThumbnailService
from app.services.converter_service import ConverterService
from worker.queue import QueueConfig, JobData, JobResult
from worker.processor import JobProcessor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, config: Optional[QueueConfig] = None):
        self.config = config or QueueConfig()
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self.processor: Optional[JobProcessor] = None
        self._running = False

    async def initialize(self):
        await self._init_services()
        await self._connect()
        logger.info("Worker initialized")

    async def _init_services(self):
        storage = get_storage_service()
        thumbnail_service = ThumbnailService(temp_dir=os.getenv("TEMP_DIR", "/tmp/thumbnails"))
        converter_service = ConverterService(temp_dir=os.getenv("TEMP_DIR", "/tmp/conversions"))
        
        self.processor = JobProcessor(self.config)
        self.processor.storage = storage
        self.processor.thumbnail_service = thumbnail_service
        self.processor.converter_service = converter_service

    async def _connect(self):
        self.connection = await aio_pika.connect_robust(self.config.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=self.config.max_concurrent)
        
        self.queue = await self.channel.declare_queue(
            self.config.queue_name,
            durable=True
        )
        
        logger.info(f"Connected to RabbitMQ, queue: {self.config.queue_name}")

    async def _process_message(self, message: AbstractIncomingMessage):
        async with message.process():
            try:
                body = message.body.decode()
                data = JobData.from_dict(body)
                
                logger.info(f"Received job: {data.job_type} - {data.job_id}")
                
                result = await self.processor.process(data)
                
                if data.webhook_url:
                    await self._send_webhook(data.webhook_url, result)
                
                if result.success:
                    logger.info(f"Job completed: {result.job_id}")
                else:
                    logger.error(f"Job failed: {result.job_id} - {result.error}")
                    
            except Exception as e:
                logger.exception(f"Message processing failed: {e}")

    async def _send_webhook(self, url: str, result: JobResult):
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=result.to_dict())
        except Exception as e:
            logger.warning(f"Webhook notification failed: {e}")

    async def start(self):
        await self.initialize()
        self._running = True
        
        logger.info("Worker started, waiting for jobs...")
        
        await self.queue.consume(self._process_message)
        
        while self._running:
            await asyncio.sleep(1)

    async def stop(self):
        self._running = False
        
        if self.connection:
            await self.connection.close()
        
        logger.info("Worker stopped")


async def main():
    config = QueueConfig(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "amqp://localhost:5672"),
        queue_name=os.getenv("QUEUE_NAME", "unoconv-jobs"),
        max_concurrent=int(os.getenv("MAX_CONCURRENT", "2")),
        job_timeout=int(os.getenv("JOB_TIMEOUT", "300"))
    )
    
    worker = Worker(config)
    
    loop = asyncio.get_event_loop()
    
    def signal_handler(sig):
        logger.info(f"Received signal {sig}, shutting down...")
        loop.create_task(worker.stop())
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())