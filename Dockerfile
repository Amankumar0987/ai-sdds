FROM python:3.12-slim

# OS-level dependencies only — no compilers/dev-tools left in the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Only the lean, API-serving requirements are installed here.
# torch/flwr/ultralytics (training-only, ~3-4GB) live in
# requirements-fl.txt and are NOT needed to run the API — installing
# them here is what was blowing up the Railway build/image size.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY api/ ./api/
COPY config.py .

# Never run the app as root inside the container
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# Railway (and most PaaS hosts) inject a dynamic $PORT at runtime and
# route traffic to it — a container that only listens on a hardcoded
# 8000 will fail health checks / "application failed to respond" on
# Railway if Railway happens to assign a different port. Default to
# 8000 for local `docker run` where no PORT is set.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", 8000)}/v1/health')" || exit 1

# Shell form (not exec-array form) so $PORT is actually substituted.
CMD uvicorn api.app:app --host 0.0.0.0 --port ${PORT}
