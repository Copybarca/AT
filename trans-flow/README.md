# trans-flow

Асинхронный HTTP-сервис агентного перевода одного текстового фрагмента.
Сервис не имеет доступа к PostgreSQL: `trans-api` передаёт PK сегмента и текст,
а результат возвращается в доверенный callback `trans-api`.

## Запуск

```bash
uv sync --dev
uv run uvicorn trans_flow.app:app --host 127.0.0.1 --port 8003
```

Перед запуском Ollama должна обслуживать настроенную модель, например:

```bash
ollama pull qwen3:8b
```

## API

- `POST /internal/v1/translations` — принять одну команду перевода и вернуть
  `202 Accepted` после помещения в bounded queue;
- `GET /health` — health check.

Команда требует `Authorization: Bearer <SERVICE_TOKEN>` и
`Idempotency-Key: translation-<processId>-<segmentId>`. Она содержит
`processId`, `bookId`, PK сегмента, stable key, source hash, исходный текст,
языки и относительный callback path.

Worker переводит ровно один фрагмент через Ollama. После успеха или ошибки он
вызывает callback `trans-api`. Следующий фрагмент выбирает только `trans-api`
после commit предыдущего перевода.

## Настройки

```text
SERVICE_TOKEN=local-service-token
TRANS_API_BASE_URL=http://localhost:8080
TRANSLATION_QUEUE_CAPACITY=16
TRANSLATION_WORKER_COUNT=1
TRANSLATION_CALLBACK_RETRIES=3
TRANSLATION_CALLBACK_RETRY_DELAY_SECONDS=1
TRANSLATION_TIMEOUT_SECONDS=300
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
```

## Проверка

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```
