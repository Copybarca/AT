# PDF-extractor

Асинхронный FastAPI-сервис с одной ответственностью: извлечь из PDF упорядоченные текстовые фрагменты, код, изображения и OCR-области, затем передать цельный результат в `trans-api`.

## Запуск

```bash
uv sync --dev
uv run uvicorn pdf_extractor.app:app --host 127.0.0.1 --port 8001
```

Для OCR нужны системный Tesseract и языковые пакеты. Тесты используют детерминированные adapters и не запускают реальный OCR.

## API

- `POST /internal/v1/extractions` — multipart-команда `request` + `file`, возвращает 202 после постановки в bounded queue;
- `GET /internal/v1/settings/fragmentation` — текущие настройки новых jobs;
- `PUT /internal/v1/settings/fragmentation` — атомарная замена настроек новых jobs;
- `GET /health` — health check.

Внутренние ручки требуют `Authorization: Bearer <SERVICE_TOKEN>`. Extraction command требует `Idempotency-Key: extraction-<processId>`.

## Основные настройки

```text
TRANS_API_BASE_URL=http://localhost:8080
SERVICE_TOKEN=local-service-token
EXTRACTION_QUEUE_CAPACITY=4
EXTRACTION_WORKER_COUNT=1
EXTRACTION_BATCH_SIZE=100
EXTRACTION_TEMP_ROOT=/tmp/pdf-extractor
MAX_REQUEST_BYTES=1073741824
MIN_SELECTABLE_CHARACTERS=8
OCR_DPI=300
OCR_LANGUAGE=eng
FRAGMENT_MIN_SENTENCES=5
FRAGMENT_MAX_SENTENCES=10
FRAGMENT_BOUNDARY_TOLERANCE_SENTENCES=2
```

Каждый принятый job хранит immutable snapshot настроек фрагментации. Рабочий сервис не имеет доступа к PostgreSQL или S3.

## Проверка

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```
