import asyncio
import json
import aio_pika
import logging
import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
import warnings
import tempfile
import os
from datetime import datetime
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from app.db.models.processing_job import ProcessingJob, Base
from app.core.config import settings

warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf.symbol_database')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

TFLITE_MODEL_PATH = 'asl_action_recognizer.tflite'
POSE_MODEL_PATH = 'pose_landmarker_lite.task'
HAND_MODEL_PATH = 'hand_landmarker.task'

if not all(os.path.exists(p) for p in [TFLITE_MODEL_PATH, POSE_MODEL_PATH, HAND_MODEL_PATH]):
    raise RuntimeError("Error: One or more model files are missing.")

ACTIONS = np.array(['obrigado', 'null'])
SEQUENCE_LENGTH = 100
CONFIDENCE_THRESHOLD = 0.75

try:
    interpreter = tf.lite.Interpreter(model_path=TFLITE_MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    logger.info("TensorFlow Lite model loaded successfully.")
except Exception as e:
    raise RuntimeError(f"Error loading TFLite model: {e}")

base_options = python.BaseOptions
PoseLandmarker = vision.PoseLandmarker
PoseLandmarkerOptions = vision.PoseLandmarkerOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
VisionRunningMode = vision.RunningMode

pose_options = PoseLandmarkerOptions(
    base_options=base_options(model_asset_path=POSE_MODEL_PATH), 
    running_mode=VisionRunningMode.IMAGE
)
hand_options = HandLandmarkerOptions(
    base_options=base_options(model_asset_path=HAND_MODEL_PATH), 
    running_mode=VisionRunningMode.IMAGE, 
    num_hands=2
)

pose_landmarker = PoseLandmarker.create_from_options(pose_options)
hand_landmarker = HandLandmarker.create_from_options(hand_options)
logger.info("MediaPipe landmarkers created successfully.")


def extract_keypoints(pose_result, hand_result):
    pose = np.array([[res.x, res.y, res.z, res.visibility] for res in pose_result.pose_landmarks[0]]).flatten() if pose_result.pose_landmarks else np.zeros(33 * 4)
    lh, rh = np.zeros(21 * 3), np.zeros(21 * 3)
    if hand_result.hand_landmarks:
        for i, hand_landmarks in enumerate(hand_result.hand_landmarks):
            handedness = hand_result.handedness[i][0].category_name
            if handedness == "Left":
                lh = np.array([[res.x, res.y, res.z] for res in hand_landmarks]).flatten()
            elif handedness == "Right":
                rh = np.array([[res.x, res.y, res.z] for res in hand_landmarks]).flatten()
    return np.concatenate([pose, lh, rh])


def process_video(video_hex: str, expected_action: str) -> dict:
    try:
        video_content = bytes.fromhex(video_hex)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            temp_video.write(video_content)
            temp_video_path = temp_video.name

        frame_landmarks = []
        cap = None
        try:
            cap = cv2.VideoCapture(temp_video_path)
            if not cap.isOpened():
                return {"action_found": False, "error": "Could not open video file"}

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                pose_result = pose_landmarker.detect(mp_image)
                hand_result = hand_landmarker.detect(mp_image)
                keypoints = extract_keypoints(pose_result, hand_result)
                frame_landmarks.append(keypoints)

        finally:
            if cap:
                cap.release()
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

        if not frame_landmarks:
            return {"action_found": False, "error": "Could not extract frames or landmarks"}

        if len(frame_landmarks) >= SEQUENCE_LENGTH:
            indices = np.linspace(0, len(frame_landmarks) - 1, SEQUENCE_LENGTH, dtype=int)
            final_sequence = np.array([frame_landmarks[i] for i in indices])
        else:
            final_sequence = np.array(frame_landmarks)
            padding = np.array([frame_landmarks[-1]] * (SEQUENCE_LENGTH - len(frame_landmarks)))
            final_sequence = np.vstack([final_sequence, padding])

        input_data = np.expand_dims(final_sequence, axis=0).astype(np.float32)
        
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])
        prediction = output_data[0]
        
        predicted_action = ACTIONS[np.argmax(prediction)]
        confidence = float(prediction[np.argmax(prediction)])

        action_found = bool(predicted_action == expected_action and confidence >= CONFIDENCE_THRESHOLD)

        return {
            "action_found": action_found,
            "predicted_action": str(predicted_action),
            "confidence": f"{confidence:.2%}",
            "expected_action": expected_action,
            "is_match": bool(predicted_action == expected_action)
        }

    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return {"action_found": False, "error": str(e)}


async def process_message(message: aio_pika.abc.AbstractIncomingMessage, db: AsyncSession) -> None:
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            job_id = body.get("job_id")
            expected_action = body.get("expected_action")
            video_content = body.get("video_content")

            logger.info(f"Processing job {job_id} for action: {expected_action}")

            result = process_video(video_content, expected_action)
            
            db_result = await db.execute(
                select(ProcessingJob).filter(ProcessingJob.job_id == job_id)
            )
            job = db_result.scalars().first()
            
            if job:
                job.status = "completed"
                job.action_found = result.get("action_found")
                job.predicted_action = result.get("predicted_action")
                job.confidence = result.get("confidence")
                job.is_match = result.get("is_match")
                job.completed_at = datetime.utcnow()
                job.result = result
                
                if "error" in result:
                    job.error = result["error"]
                
                await db.commit()
                logger.info(f"Job {job_id} completed: {result.get('action_found')}")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            try:
                body = json.loads(message.body.decode())
                job_id = body.get("job_id")
                db_result = await db.execute(
                    select(ProcessingJob).filter(ProcessingJob.job_id == job_id)
                )
                job = db_result.scalars().first()
                if job:
                    job.status = "failed"
                    job.error = str(e)
                    job.completed_at = datetime.utcnow()
                    await db.commit()
            except Exception as ex:
                logger.error(f"Error updating job status: {str(ex)}")


async def main():
    await init_db()
    
    db = SessionLocal()
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        logger.info("Connected to RabbitMQ")

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await channel.declare_queue('video_processing_queue', durable=True)

            logger.info("Video processing worker started, waiting for jobs...")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await process_message(message, db)

    except Exception as e:
        logger.error(f"Worker error: {str(e)}")
        await asyncio.sleep(5)
        await main()
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped")