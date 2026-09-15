# Dockerfile — Raspberry Pi Weather Station (desktop/mock mode in a container)
#
# The container runs the full stack (FastAPI + dashboard + supervised tasks)
# with mock hardware — no GPIO inside Docker. On a real Pi, run bare-metal:
#   pip install -r requirements.txt && python main.py
#
# Build & run:
#   docker compose up -d          # or: docker build -t weatherstation .

FROM python:3.11-slim

# espeak enables Voice Mode speech synthesis inside the container
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng espeak \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY main.py config.py config_io.py database.py ./
COPY hardware ./hardware
COPY services ./services
COPY utils ./utils
COPY web ./web

# Non-root runtime
RUN useradd --create-home --shell /bin/bash weather \
    && chown -R weather:weather /app
USER weather

ENV WEATHER_HOST=0.0.0.0 \
    WEATHER_PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Volume mount point for SQLite persistence (see docker-compose.yml)
VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1

CMD ["python", "main.py"]
