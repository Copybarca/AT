# document-builder

Асинхронный FastAPI-сервис с одной ответственностью: принять полный immutable пакет элементов и изображений, собрать его единственным WeasyPrint renderer, независимо проверить через PyPDF и отправить raw PDF обратно в `trans-api`.

## Запуск

```bash
uv sync --dev
uv run uvicorn document_builder.app:app --host 127.0.0.1 --port 8002
```

## API

- `POST /internal/v1/builds` — multipart с JSON-частью `request` и повторяемыми image-частями `asset`, каждая с `X-Asset-Key`;
- `GET /health` — health check.

Команда требует `Authorization: Bearer <TRANS_API_TOKEN>` и `Idempotency-Key: build-<processId>`. После 202 builder не запрашивает дополнительные данные. Результат отправляется на доверенный callback как raw `application/pdf`.

## Основные настройки

```text
TRANS_API_BASE_URL=http://localhost:8080
TRANS_API_TOKEN=local-service-token
BUILD_QUEUE_CAPACITY=4
BUILD_WORKER_COUNT=1
BUILD_MAX_REQUEST_BYTES=1073741824
BUILD_MAX_ELEMENTS=100000
BUILD_MAX_IMAGE_BYTES=52428800
BUILD_MAX_IMAGE_PIXELS=100000000
BUILD_TEMP_ROOT=/tmp/document-builder
BUILD_TIMEOUT_SECONDS=1800
BUILD_CALLBACK_RETRIES=3
BUILD_CALLBACK_RETRY_DELAY_SECONDS=5
PAGE_WIDTH_IN=7
PAGE_HEIGHT_IN=9.1875
PAGE_MARGIN_TOP_IN=0.68
PAGE_MARGIN_RIGHT_IN=0.72
PAGE_MARGIN_BOTTOM_IN=0.72
PAGE_MARGIN_LEFT_IN=0.72
BODY_FONT_FAMILY=Noto Serif
MONO_FONT_FAMILY=IBM Plex Mono
BODY_FONT_SIZE_PT=10.5
```

Сервис не имеет доступа к БД или S3 и не выполняет OCR/перевод.

## Проверка

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```
