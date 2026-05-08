FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg fonts-dejavu curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
RUN mkdir -p output/songs output/videos output/shorts output/logs output/brainrot output/ai_model
CMD ["python", "/app/deploy.py"]
