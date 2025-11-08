# Use NVIDIA CUDA base image instead of slim
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Install Python 3.11 and pip
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python and pip
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

# Set the working directory inside the container.
WORKDIR /app

# Copy the dependency file.
COPY requirements.txt .

# Install Python dependencies, including Gunicorn.
RUN python3.11 -m pip install --upgrade pip && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# EXPLICITLY copy model files to ensure they're included
COPY klibras_model.h5 .
COPY pose_landmarker_lite.task .
COPY hand_landmarker.task .
COPY face_landmarker.task .

# Verify model files are present
RUN echo "=== Verifying model files ===" && \
    ls -lh /app/*.task /app/*.h5 && \
    echo "=== Model files verified ===" || \
    (echo "ERROR: Model files missing!" && exit 1)

# Expose the port the app will run on.
EXPOSE 8000

# Run the application using Gunicorn with Uvicorn workers for ASGI compatibility.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]