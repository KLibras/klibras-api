import uuid
import json
import aio_pika
from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.dependencies import get_current_user
from app.models.user import User
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

job_results = {}

RABBITMQ_URL = "amqp://guest:guest@localhost/"

async def get_rabbitmq_connection():
    return await aio_pika.connect_robust(RABBITMQ_URL)

@router.post("/check_action", status_code=status.HTTP_202_ACCEPTED)
async def check_action(
    expected_action: str = Form(...),
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    job_id = str(uuid.uuid4())
    video_content = await video.read()
    logger.info("check action called with expected sign ")

    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue('video_processing_queue', durable=True)
        
        message_body = {
            "job_id": job_id,
            "expected_action": expected_action,
            "video_content": video_content.hex()
        }
        
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key='video_processing_queue',
        )

    job_results[job_id] = {"status": "processing"}
    
    return JSONResponse(
        content={"jobId": job_id, "status": "processing"},
        status_code=status.HTTP_202_ACCEPTED
    )

@router.get("/results/{job_id}")
async def get_job_result(job_id: str, current_user: User = Depends(get_current_user)):
    result = job_results.get(job_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    response = result.copy()
    response["jobId"] = job_id
    return response