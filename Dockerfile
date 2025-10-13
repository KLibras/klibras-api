# Start with a lightweight Python base image.
FROM python:3.11-slim

# THIS IS THE FIX: Install system libraries required for dependencies like OpenCV.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0

# Set the working directory inside the container.
WORKDIR /app

# Copy the dependency file.
COPY requirements.txt .

# Install Python dependencies, including Gunicorn.
# Make sure 'gunicorn' is listed in your requirements.txt file.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container.
COPY . .

# Expose the port the app will run on.
EXPOSE 8000

# Run the application using Gunicorn with Uvicorn workers for ASGI compatibility.
# -w 4: Starts 4 worker processes.
# -k uvicorn.workers.UvicornWorker: Tells Gunicorn to use Uvicorn workers for async apps.
# --bind 0.0.0.0:8000: Binds the server to port 8000 on all network interfaces.
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
