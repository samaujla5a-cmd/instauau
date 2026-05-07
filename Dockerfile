FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg fonts-dejavu curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp \
    -o /usr/local/bin/yt-dlp && chmod a+rx /usr/local/bin/yt-dlp

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN mkdir -p output/songs output/videos output/shorts output/logs \
              output/brainrot output/ai_model output/sessions

CMD ["python", "/app/deploy.py"]
