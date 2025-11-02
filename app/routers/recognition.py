import uuid
import json
import aio_pika
import asyncio
from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.db.models.processing_job import ProcessingJob
from app.core.config import settings
from datetime import datetime
import logging

router = APIRouter()
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
    job_id = str(uuid.uuid4())
    video_content = await video.read()
    logger.info(f"check action called with expected sign: {expected_action} by user {current_user.id}")

    try:
        connection = await get_rabbitmq_connection()
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue('video_processing_queue', durable=True)
            
            # Use base64 encoding instead of hex - more efficient (75% of hex size)
            import base64
            message_body = {
                "job_id": job_id,
                "expected_action": expected_action,
                "video_content": base64.b64encode(video_content).decode('utf-8'),
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
            status="pending"
        )
        db.add(job)
        await db.commit()
        
        logger.info(f"Job {job_id} queued for processing")
        
        return JSONResponse(
            content={"jobId": job_id, "status": "pending"},
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
    wait: bool = Query(default=False, description="Wait for job completion (long polling)"),
    timeout: int = Query(default=10, ge=1, le=120, description="Timeout in seconds for waiting"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    
    if wait:
        start_time = asyncio.get_event_loop().time()
        poll_delay = 0.1  # Start with 100ms delay
        max_poll_delay = 2.0  # Maximum 2s between polls
        
        while True:
            db.expire_all()
            
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
            
            if job.status in ["completed", "failed"]:
                logger.info(f"Job {job_id} finished with status: {job.status}")
                return {
                    "jobId": job.job_id,
                    "status": job.status,
                    "actionFound": job.action_found,
                    "predictedAction": job.predicted_action,
                    "confidence": job.confidence,
                    "isMatch": job.is_match,
                    "expectedAction": job.expected_action,
                    "error": job.error,
                    "createdAt": job.created_at.isoformat() if job.created_at else None,
                    "completedAt": job.completed_at.isoformat() if job.completed_at else None
                }
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.info(f"Job {job_id} timeout after {elapsed:.2f}s, status: {job.status}")
                return {
                    "jobId": job.job_id,
                    "status": job.status,
                    "message": "Job still processing, check again later",
                    "actionFound": None,
                    "predictedAction": None,
                    "confidence": None,
                    "isMatch": None,
                    "expectedAction": job.expected_action,
                    "error": None,
                    "createdAt": job.created_at.isoformat() if job.created_at else None,
                    "completedAt": None
                }
            
            # Exponential backoff for polling
            await asyncio.sleep(poll_delay)
            poll_delay = min(poll_delay * 1.5, max_poll_delay)
    
    else:
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
            "createdAt": job.created_at.isoformat() if job.created_at else None,
            "completedAt": job.completed_at.isoformat() if job.completed_at else None
        }


@router.get("/jobs/user/history")
async def get_user_job_history(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProcessingJob)
        .filter(ProcessingJob.user_id == current_user.id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()
    
    return {
        "jobs": [
            {
                "jobId": job.job_id,
                "status": job.status,
                "actionFound": job.action_found,
                "predictedAction": job.predicted_action,
                "confidence": job.confidence,
                "isMatch": job.is_match,
                "expectedAction": job.expected_action,
                "error": job.error,
                "createdAt": job.created_at.isoformat() if job.created_at else None,
                "completedAt": job.completed_at.isoformat() if job.completed_at else None
            }
            for job in jobs
        ],
        "total": len(jobs),
        "limit": limit,
        "offset": offset
    }