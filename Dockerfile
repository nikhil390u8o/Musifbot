FROM python:3.9-slim

# Install system dependencies for pytgcalls, youtube-dl, and ffmpeg-python
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    libopus-dev \
    pkg-config \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Upgrade pip to avoid version-related issues
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --retries 5

# Create downloads directory for youtube-dl
RUN mkdir -p /app/downloads

# Copy application code
COPY . .

# Expose port for starlette/uvicorn
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
