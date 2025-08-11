FROM python:3.9-slim

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

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --retries 5

RUN mkdir -p /app/downloads

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
