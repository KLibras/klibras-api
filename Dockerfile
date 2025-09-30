# Start with a Python base image
FROM python:3.11-slim

# THIS IS THE FIX: Install all required system libraries for OpenCV
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .
# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]