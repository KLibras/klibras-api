import uuid
import json
import aio_pika
from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.db.models.processing_job import ProcessingJob
from app.core.config import settings
from datetime import datetime
import logging

router = APIRouter(prefix="/api/video", tags=["video"])
logger = logging.getLogger(__name__)

async def get_rabbitmq_connection():
    try:
        return await aio_pika.connect_robust(settings.rabbitmq_url)
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message queue service unavailable"
        )

@router.post("/check_action", status_code=status.HTTP_202_ACCEPTED)
async def check_action(
    expected_action: str = Form(...),
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload video for sign language action verification"""
    job_id = str(uuid.uuid4())
    video_content = await video.read()
    logger.info(f"check action called with expected sign: {expected_action} by user {current_user.id}")

    try:
        connection = await get_rabbitmq_connection()
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue('video_processing_queue', durable=True)
            
            message_body = {
                "job_id": job_id,
                "expected_action": expected_action,
                "video_content": video_content.hex(),
                "user_id": current_user.id
            }
            
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message_body).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_encoding='utf-8'
                ),
                routing_key='video_processing_queue',
            )

        job = ProcessingJob(
            job_id=job_id,
            user_id=current_user.id,
            expected_action=expected_action,
            status="processing"
        )
        db.add(job)
        await db.commit()
        
        logger.info(f"Job {job_id} queued for processing")
        
        return JSONResponse(
            content={"jobId": job_id, "status": "processing"},
            status_code=status.HTTP_202_ACCEPTED
        )
    
    except Exception as e:
        logger.error(f"Error queuing job: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue video for processing"
        )

@router.get("/results/{job_id}")
async def get_job_result(
    job_id: str, 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get video processing results"""
    result = await db.execute(
        select(ProcessingJob).filter(
            ProcessingJob.job_id == job_id,
            ProcessingJob.user_id == current_user.id
        )
    )
    job = result.scalars().first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Job not found"
        )
    
    return {
        "jobId": job.job_id,
        "status": job.status,
        "actionFound": job.action_found,
        "predictedAction": job.predicted_action,
        "confidence": job.confidence,
        "isMatch": job.is_match,
        "expectedAction": job.expected_action,
        "error": job.error,
        "createdAt": job.created_at,
        "completedAt": job.completed_at
    }