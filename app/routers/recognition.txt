import uuid
import json
import aio_pika
from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


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
    """Analisa um vídeo para verificar se ele contém a ação esperada.

    Este endpoint recebe um vídeo e uma string com a ação esperada,
    processa o vídeo e retorna o resultado da predição. Requer
    autenticação para ser acessado.

    Args:
        expected_action (str): Ação esperada, recebida via formulário.
        video (UploadFile): O arquivo de vídeo enviado para análise.
        current_user (User): O usuário autenticado, injetado pela dependência.

    Returns:
        Any: O resultado retornado pelo serviço de processamento de vídeo.
    """
    job_id = str(uuid.uuid4())
    video_content = await video.read()

    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()
        message_body = {
            "job_id": job_id,
            "expected_action": expected_action,
            "video_content": video_content.hex() # Serialize the video content
        }
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(message_body).encode()),
            routing_key='video_processing_queue',
        )

    job_results[job_id] = {"status": "processing"}
    return JSONResponse(
        content={"job_id": job_id, "status": "accepted"},
        status_code=status.HTTP_202_ACCEPTED
    )

@router.get("/results/{job_id}")
async def get_job_result(job_id: str, current_user: User = Depends(get_current_user)):
    """
    Retrieves the result of a video processing job.
    """
    result = job_results.get(job_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return result