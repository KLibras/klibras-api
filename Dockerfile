# Start with a lightweight Python base image.
FROM python:3.11-slim

# Install system libraries required for dependencies like OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container.
WORKDIR /app

# Copy the dependency file.
COPY requirements.txt .

# Install Python dependencies, including Gunicorn.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# EXPLICITLY copy model files to ensure they're included
COPY asl_model.tflite .
COPY asl_action_recognizer.h5 .
COPY pose_landmarker_lite.task .
COPY hand_landmarker.task .

# Verify model files are present
RUN echo "=== Verifying model files ===" && \
    ls -lh /app/*.tflite /app/*.task /app/*.h5 && \
    echo "=== Model files verified ===" || \
    (echo "ERROR: Model files missing!" && exit 1)

# Expose the port the app will run on.
EXPOSE 8000

# Run the application using Gunicorn with Uvicorn workers for ASGI compatibility.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]