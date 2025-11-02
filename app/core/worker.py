"""
 Criação do worker do RabbitMQ e funções de reconhecimento dos sinais
"""

import asyncio
import json
import base64
import aio_pika
import logging
import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
import warnings
import tempfile
import os
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from app.db.models.processing_job import ProcessingJob, Base
from app.core.config import settings

warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf.symbol_database')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração da GPU 
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# Configura o TensorFlow
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        
        # Precisão mista para os Tensor Cores
        policy = tf.keras.mixed_precision.Policy('mixed_float16')
        tf.keras.mixed_precision.set_global_policy(policy)
        
        logger.info(f"GPU disponível: {gpus}")
        logger.info(f"Precisão mista ativada para otimização da T4")
    except RuntimeError as e:
        logger.error(f"Erro na configuração da GPU: {e}")
else:
    logger.warning("Nenhuma GPU detectada - executando na CPU")

# Configuração do banco de dados
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Caminhos dos modelos
H5_MODEL_PATH = 'asl_action_recognizer.h5'
POSE_MODEL_PATH = 'pose_landmarker_lite.task'
HAND_MODEL_PATH = 'hand_landmarker.task'
FACE_MODEL_PATH = 'face_landmarker.task'

# Encontrar modelos
for base_path in ['/app', '/app/models', '.']:
    if all(os.path.exists(os.path.join(base_path, f)) for f in [
        'asl_action_recognizer.h5',
        'pose_landmarker_lite.task',
        'hand_landmarker.task',
        'face_landmarker.task'
    ]):
        H5_MODEL_PATH = os.path.join(base_path, 'asl_action_recognizer.h5')
        POSE_MODEL_PATH = os.path.join(base_path, 'pose_landmarker_lite.task')
        HAND_MODEL_PATH = os.path.join(base_path, 'hand_landmarker.task')
        FACE_MODEL_PATH = os.path.join(base_path, 'face_landmarker.task')
        logger.info(f"✓ Modelos encontrados em {base_path}")
        break
else:
    logger.error(f"✗ Arquivos de modelo não encontrados em: /app, /app/models, .")
    logger.error(f"  Procurando por: asl_action_recognizer.h5, pose_landmarker_lite.task, hand_landmarker.task, face_landmarker.task")
    logger.error(f"  Diretório de trabalho atual: {os.getcwd()}")
    if os.path.exists('/app'):
        logger.error(f"  Conteúdo de /app: {os.listdir('/app')}")
    raise RuntimeError("Erro: Um ou mais arquivos de modelo estão faltando.")

# Configuração otimizada para precisão com velocidade razoável
ACTIONS = np.array(['obrigado', 'tudo_bem', "qual_seu_nome", 'bom_dia', 'null'])
SEQUENCE_LENGTH = 100  # Manter original - você fará downsample para isto
TARGET_FRAMES = 70   # Extrair 70 frames de 90 (pular a cada ~1.3 frames)
CONFIDENCE_THRESHOLD = 0.75
PROCESS_WIDTH = 480  # Reduzir escala para velocidade sem perder detalhes
MAX_WORKERS = 4  # Threads de detecção paralelas
CONCURRENT_VIDEOS = 2  # Processar 2 vídeos simultaneamente na T4

# Carregar modelo Keras
try:
    keras_module = getattr(tf, 'keras')
    model = keras_module.models.load_model(H5_MODEL_PATH)
    logger.info("Modelo TensorFlow Keras carregado com sucesso.")
    logger.info(f"Shape de entrada do modelo: {model.input_shape}")
    logger.info(f"Shape de saída do modelo: {model.output_shape}")
except Exception as e:
    raise RuntimeError(f"Erro ao carregar o modelo Keras: {e}")

# Configuração do MediaPipe
base_options = python.BaseOptions
PoseLandmarker = vision.PoseLandmarker
PoseLandmarkerOptions = vision.PoseLandmarkerOptions
HandLandmarker = vision.HandLandmarker
HandLandmarkerOptions = vision.HandLandmarkerOptions
FaceLandmarker = vision.FaceLandmarker
FaceLandmarkerOptions = vision.FaceLandmarkerOptions
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
face_options = FaceLandmarkerOptions(
    base_options=base_options(model_asset_path=FACE_MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    num_faces=1
)

pose_landmarker = PoseLandmarker.create_from_options(pose_options)
hand_landmarker = HandLandmarker.create_from_options(hand_options)
face_landmarker = FaceLandmarker.create_from_options(face_options)
logger.info("Landmarkers do MediaPipe (pose, hand, face) criados com sucesso.")


def extract_keypoints_with_face(pose_result, hand_result, face_result):
    """
    Extrai todos os keypoints incluindo marcos faciais completos para precisão.
    Total de features: 132 (pose) + 63 (mão esquerda) + 63 (mão direita) + 1434 (rosto) = 1692
    """
    # Pose: 33 marcos * 4 (x, y, z, visibilidade) = 132
    pose = np.array([[res.x, res.y, res.z, res.visibility] 
                        for res in pose_result.pose_landmarks[0]]).flatten() \
            if pose_result.pose_landmarks else np.zeros(33 * 4)
    
    # Mãos: 21 marcos * 3 (x, y, z) cada = 63 por mão
    lh, rh = np.zeros(21 * 3), np.zeros(21 * 3)
    if hand_result.hand_landmarks:
        for i, hand_landmarks in enumerate(hand_result.hand_landmarks):
            handedness = hand_result.handedness[i][0].category_name
            if handedness == "Left":
                lh = np.array([[res.x, res.y, res.z] 
                                for res in hand_landmarks]).flatten()
            elif handedness == "Right":
                rh = np.array([[res.x, res.y, res.z] 
                                for res in hand_landmarks]).flatten()
    
    # Rosto: 478 marcos * 3 (x, y, z) = 1434 (PRECISÃO TOTAL para toques no queixo, etc.)
    face = np.array([[res.x, res.y, res.z] 
                        for res in face_result.face_landmarks[0]]).flatten() \
            if face_result.face_landmarks else np.zeros(478 * 3)
    
    return np.concatenate([pose, lh, rh, face])


def detect_all_parallel(mp_image):
    """Executa todos os três detectores MediaPipe em paralelo para velocidade."""
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        pose_future = executor.submit(pose_landmarker.detect, mp_image)
        hand_future = executor.submit(hand_landmarker.detect, mp_image)
        face_future = executor.submit(face_landmarker.detect, mp_image)
        
        return (
            pose_future.result(),
            hand_future.result(),
            face_future.result()
        )


def process_video(video_base64: str, expected_action: str) -> dict:
    """
    Processa o vídeo com otimização de GPU mantendo a precisão.
    - Extrai ~70 frames de um vídeo típico de 90 frames
    - Usa marcos faciais completos para precisão
    - Reduz a escala para 480px de largura para velocidade
    - Detecção paralela para processamento mais rápido
    """
    try:
        video_content = base64.b64decode(video_base64)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            temp_video.write(video_content)
            temp_video_path = temp_video.name

        frame_landmarks = []
        cap = None
        start_time = time.time()
        
        try:
            cap = cv2.VideoCapture(temp_video_path)
            if not cap.isOpened():
                return {"action_found": False, "error": "Não foi possível abrir o arquivo de vídeo"}

            # Obter propriedades do vídeo
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calcular quais frames processar para obter ~70 frames
            # Se 90 frames, processar índices [0, 1, 3, 4, 6, 7, 9...] (pular a cada ~1.3)
            if total_frames <= TARGET_FRAMES:
                frame_indices_to_process = set(range(total_frames))
            else:
                # Usar linspace para amostrar uniformemente TARGET_FRAMES do total_frames
                frame_indices_to_process = set(
                    np.linspace(0, total_frames - 1, TARGET_FRAMES, dtype=int)
                )
            
            logger.info(f"Vídeo: {fps:.1f}fps, {total_frames} frames → processando {len(frame_indices_to_process)} frames")

            frame_count = 0
            extraction_times = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Processar apenas os frames selecionados
                if frame_count not in frame_indices_to_process:
                    frame_count += 1
                    continue

                frame_start = time.time()

                # Reduzir escala para processamento mais rápido
                h, w = frame.shape[:2]
                if w > PROCESS_WIDTH:
                    scale = PROCESS_WIDTH / w
                    frame = cv2.resize(frame, (PROCESS_WIDTH, int(h * scale)), 
                                       interpolation=cv2.INTER_LINEAR)

                # Converter para RGB uma vez
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                
                # Detectar todos os landmarks em paralelo
                pose_result, hand_result, face_result = detect_all_parallel(mp_image)
                
                # Extrair keypoints com marcos faciais completos
                keypoints = extract_keypoints_with_face(pose_result, hand_result, face_result)
                frame_landmarks.append(keypoints)
                
                extraction_times.append(time.time() - frame_start)
                frame_count += 1

        finally:
            if cap:
                cap.release()
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

        if not frame_landmarks:
            return {"action_found": False, "error": "Não foi possível extrair frames ou landmarks"}

        extraction_time = time.time() - start_time
        avg_frame_time = np.mean(extraction_times) if extraction_times else 0

        # Preparar sequência: reamostrar para SEQUENCE_LENGTH (100 frames)
        if len(frame_landmarks) >= SEQUENCE_LENGTH:
            indices = np.linspace(0, len(frame_landmarks) - 1, SEQUENCE_LENGTH, dtype=int)
            final_sequence = np.array([frame_landmarks[i] for i in indices])
        else:
            final_sequence = np.array(frame_landmarks)
            padding = np.array([frame_landmarks[-1]] * (SEQUENCE_LENGTH - len(frame_landmarks)))
            final_sequence = np.vstack([final_sequence, padding])

        # Inferência na GPU com precisão mista
        input_data = np.expand_dims(final_sequence, axis=0).astype(np.float32)
        
        inference_start = time.time()
        prediction = model.predict(input_data, verbose=0)[0]
        inference_time = time.time() - inference_start
        
        predicted_action = ACTIONS[np.argmax(prediction)]
        confidence = float(prediction[np.argmax(prediction)])

        action_found = bool(predicted_action == expected_action and confidence >= CONFIDENCE_THRESHOLD)

        total_time = time.time() - start_time

        return {
            "action_found": action_found,
            "predicted_action": str(predicted_action),
            "confidence": f"{confidence:.2%}",
            "expected_action": expected_action,
            "is_match": bool(predicted_action == expected_action),
            "frames_extracted": len(frame_landmarks),
            "total_frames": total_frames,
            "extraction_time_ms": f"{extraction_time * 1000:.1f}",
            "inference_time_ms": f"{inference_time * 1000:.1f}",
            "total_time_ms": f"{total_time * 1000:.1f}",
            "avg_frame_time_ms": f"{avg_frame_time * 1000:.1f}"
        }

    except Exception as e:
        logger.error(f"Erro ao processar o vídeo: {str(e)}")
        return {"action_found": False, "error": str(e)}


async def process_message(message: aio_pika.abc.AbstractIncomingMessage, db: AsyncSession) -> None:
    """Processa a mensagem recebida do RabbitMQ."""
    async with message.process():
        try:
            body = json.loads(message.body.decode())
            job_id = body.get("job_id")
            expected_action = body.get("expected_action")
            video_content = body.get("video_content")

            logger.info(f"Processando job {job_id} para a ação: {expected_action}")

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
                logger.info(f"Job {job_id} concluído em {result.get('total_time_ms')}ms: {result.get('predicted_action')} ({result.get('confidence')})")

        except Exception as e:
            logger.error(f"Erro ao processar a mensagem: {str(e)}")
            try:
                # Tenta marcar o job como falho no DB
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
                logger.error(f"Erro ao atualizar o status do job: {str(ex)}")


async def main():
    """Loop principal do worker com concorrência otimizada para GPU."""
    await init_db()
    
    # Semáforo para limitar o processamento concorrente de vídeos
    semaphore = asyncio.Semaphore(CONCURRENT_VIDEOS)
    
    async def process_with_semaphore(message, db):
        async with semaphore:
            await process_message(message, db)
    
    db = SessionLocal()
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        logger.info("Conectado ao RabbitMQ")

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=CONCURRENT_VIDEOS)
            queue = await channel.declare_queue('video_processing_queue', durable=True)

            logger.info(f"🚀 Worker GPU iniciado em g4dn.2xlarge")
            logger.info(f"    Processando {CONCURRENT_VIDEOS} vídeos concorrentemente")
            logger.info(f"    Frames alvo: {TARGET_FRAMES} por vídeo")
            logger.info(f"    Marcos faciais completos: 478 pontos (1434 features)")

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    asyncio.create_task(process_with_semaphore(message, db))

    except Exception as e:
        logger.error(f"Erro no worker: {str(e)}")
        await asyncio.sleep(5)
        await main() # Tenta reiniciar
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker parado")