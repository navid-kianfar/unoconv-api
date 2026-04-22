import os
import json
import asyncio
from typing import Optional

import aio_pika


class QueueClient:
    def __init__(
        self,
        rabbitmq_url: Optional[str] = None,
        queue_name: str = "unoconv-jobs"
    ):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://localhost:5672")
        self.queue_name = queue_name
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.declare_queue(self.queue_name, durable=True)

    async def disconnect(self):
        if self.connection:
            await self.connection.close()

    async def submit_thumbnail(
        self,
        source: dict,
        output: dict,
        options: Optional[dict] = None,
        job_id: Optional[str] = None,
        webhook_url: Optional[str] = None
    ):
        """Submit a thumbnail generation job"""
        return await self._submit({
            "job_type": "thumbnail",
            "source": source,
            "output": output,
            "options": options or {},
            "job_id": job_id,
            "webhook_url": webhook_url
        })

    async def submit_convert(
        self,
        source: dict,
        output: dict,
        options: Optional[dict] = None,
        job_id: Optional[str] = None,
        webhook_url: Optional[str] = None
    ):
        """Submit a conversion job"""
        return await self._submit({
            "job_type": "convert",
            "source": source,
            "output": output,
            "options": options or {},
            "job_id": job_id,
            "webhook_url": webhook_url
        })

    async def _submit(self, data: dict):
        if not self.channel:
            await self.connect()
        
        message = aio_pika.Message(
            body=json.dumps(data).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        await self.channel.default_exchange.publish(
            message,
            routing_key=self.queue_name
        )
        
        return data.get("job_id")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Submit jobs to unoconv-api worker")
    parser.add_argument("--type", choices=["thumbnail", "convert"], required=True)
    parser.add_argument("--source-type", choices=["stream", "local", "s3", "ftp", "sftp", "remote"], default="local")
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--output-type", choices=["stream", "local", "s3", "ftp", "sftp", "remote"], default="local")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--output-format", default="pdf")
    parser.add_argument("--webhook", help="URL to notify on completion")
    parser.add_argument("--rabbitmq", default=os.getenv("RABBITMQ_URL", "amqp://localhost:5672"))
    
    args = parser.parse_args()
    
    client = QueueClient(rabbitmq_url=args.rabbitmq)
    
    source = {"type": args.source_type}
    if args.source_type != "stream":
        source["path"] = args.source_path
    
    output = {"type": args.output_type}
    if args.output_type != "stream":
        output["path"] = args.output_path
    
    options = {"output_format": args.output_format}
    
    if args.type == "thumbnail":
        await client.submit_thumbnail(source, output, options, webhook_url=args.webhook)
    else:
        await client.submit_convert(source, output, options, webhook_url=args.webhook)
    
    print(f"Job submitted successfully")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())