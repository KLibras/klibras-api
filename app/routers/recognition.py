from fastapi import APIRouter, File, UploadFile, Form, Depends
from app.services.recognition_service import process_video_and_predict_action
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/check_action")
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
    return await process_video_and_predict_action(expected_action, video)
