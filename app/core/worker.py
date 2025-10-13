import asyncio
import json
import aio_pika
# from app.services.recognition_service import process_video_and_predict_action

job_results = {}

async def dummy_process_video(expected_action: str, video_file):
    await asyncio.sleep(5)
    return {
        "action_found": True,
        "predicted_action": expected_action,
        "confidence": "99.99%",
        "expected_action": expected_action,
        "is_match": True
    }

async def main():
    connection = await aio_pika.connect_robust("amqp://klibras:root@rabbitmq/")
    queue_name = "video_processing_queue"

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(queue_name, durable=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    body = json.loads(message.body.decode())
                    job_id = body.get("job_id")
                    expected_action = body.get("expected_action")
                    video_content = bytes.fromhex(body.get("video_content"))
                    
                    class MockUploadFile:
                        def __init__(self, content):
                            self.file = content
                        async def read(self):
                            return self.file
                        @property
                        def filename(self):
                            return "video.mp4"

                    video_file = MockUploadFile(video_content)

                    try:
                        # result = await process_video_and_predict_action(expected_action, video_file)
                        result = await dummy_process_video(expected_action, video_file)
                        job_results[job_id] = {"status": "completed", "result": result}
                    except Exception as e:
                        job_results[job_id] = {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    asyncio.run(main())

