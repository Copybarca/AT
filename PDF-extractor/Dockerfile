FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ghostscript \
        poppler-utils \
        qpdf \
        tesseract-ocr \
        tesseract-ocr-eng \
        unpaper \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv==0.12.5

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
RUN uv sync --frozen --no-dev \
    && useradd --system --uid 10001 --home /app worker \
    && mkdir -p /tmp/pdf-extractor \
    && chown -R worker:worker /tmp/pdf-extractor

USER worker
EXPOSE 8001
CMD ["uvicorn", "pdf_extractor.app:app", "--host", "0.0.0.0", "--port", "8001"]
