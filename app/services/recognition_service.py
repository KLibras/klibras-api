from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException
from app.dependencies import get_current_user
from app.models.user import User
import cv2
import numpy as np
import tensorflow as tf
import mediapipe as mp
import warnings
import tempfile
import os
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from typing import Optional

warnings.filterwarnings("ignore", category=UserWarning, module='google.protobuf.symbol_database')

# TODO! Adicionar a task de rosto

H5_MODEL_PATH = 'asl_action_recognizer.h5'
POSE_MODEL_PATH = 'pose_landmarker_lite.task'
HAND_MODEL_PATH = 'hand_landmarker.task'

if not all(os.path.exists(p) for p in [H5_MODEL_PATH, POSE_MODEL_PATH, HAND_MODEL_PATH]):
    raise RuntimeError("Error: One or more model files are missing. Make sure .h5 and .task files are in the directory.")

ACTIONS = np.array(['obrigado', 'null'])
SEQUENCE_LENGTH = 100
CONFIDENCE_THRESHOLD = 0.75

# Lazy loading with singleton pattern for better performance
_model: Optional[tf.keras.Model] = None
_pose_landmarker: Optional[vision.PoseLandmarker] = None
_hand_landmarker: Optional[vision.HandLandmarker] = None


def get_model():
    """Lazy load TensorFlow model (singleton pattern)"""
    global _model
    if _model is None:
        try:
            _model = tf.keras.models.load_model(H5_MODEL_PATH)  # type: ignore
            print("TensorFlow model loaded successfully.")
        except Exception as e:
            raise RuntimeError(f"Error loading Keras model: {e}")
    return _model


def get_landmarkers():
    """Lazy load MediaPipe landmarkers (singleton pattern)"""
    global _pose_landmarker, _hand_landmarker
    
    if _pose_landmarker is None or _hand_landmarker is None:
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

        _pose_landmarker = PoseLandmarker.create_from_options(pose_options)
        _hand_landmarker = HandLandmarker.create_from_options(hand_options)
        print("MediaPipe landmarkers created successfully.")
    
    return _pose_landmarker, _hand_landmarker


def extract_keypoints(pose_result, hand_result):
    """Extrai os pontos-chave da pose e das mãos a partir dos resultados do MediaPipe.

    Args:
        pose_result: O resultado da detecção de pose do MediaPipe.
        hand_result: O resultado da detecção de mãos do MediaPipe.

    Returns:
        np.ndarray: Um array numpy concatenado com todos os pontos-chave.
    """
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


async def process_video_and_predict_action(expected_action: str, video: UploadFile):
    """Processa um vídeo, extrai pontos-chave e prevê a ação executada.

    Args:
        expected_action (str): A ação que se espera encontrar no vídeo.
        video (UploadFile): O arquivo de vídeo a ser processado.

    Returns:
        dict: Um dicionário contendo o resultado da predição e a confiança.
    """
    if not video.filename or not video.filename.lower().endswith('.mp4'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an MP4 video.")

    # Get models using lazy loading
    model = get_model()
    pose_landmarker, hand_landmarker = get_landmarkers()

    temp_video_path = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
        temp_video.write(await video.read())
        temp_video_path = temp_video.name

    frame_landmarks = []
    cap = None
    try:
        cap = cv2.VideoCapture(temp_video_path)
        if not cap.isOpened():
            raise HTTPException(status_code=500, detail="Could not open video file.")

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
        raise HTTPException(status_code=400, detail="Could not extract any frames or landmarks from the video.")

    if len(frame_landmarks) >= SEQUENCE_LENGTH:
        indices = np.linspace(0, len(frame_landmarks) - 1, SEQUENCE_LENGTH, dtype=int)
        final_sequence = [frame_landmarks[i] for i in indices]
    else:
        final_sequence = list(frame_landmarks)
        padding = [frame_landmarks[-1]] * (SEQUENCE_LENGTH - len(frame_landmarks))
        final_sequence.extend(padding)

    prediction = model.predict(np.expand_dims(final_sequence, axis=0))[0]
    predicted_action = ACTIONS[np.argmax(prediction)]
    confidence = float(prediction[np.argmax(prediction)])

    action_found = bool(predicted_action == expected_action and confidence >= CONFIDENCE_THRESHOLD)

    return {
        "action_found": action_found,
        "predicted_action": predicted_action,
        "confidence": f"{confidence:.2%}",
        "expected_action": expected_action,
        "is_match": bool(predicted_action == expected_action)
    }



