# AT services

Монорепозиторий содержит четыре backend-сервиса сквозного конвейера извлечения,
пофрагментного перевода и сборки PDF, а также подготовительную область общего
веб-интерфейса.

| Сервис | Стек | Назначение |
| --- | --- | --- |
| `PDF-extractor` | Python 3.12, FastAPI, uv | Извлечение текста из текстовых и сканированных PDF |
| `document-builder` | Python 3.12, FastAPI, uv | Вёрстка книг и генерация PDF |
| `trans-api` | Java 21, Spring Boot, Maven | Внешний backend API перевода |
| `trans-flow` | Python 3.12, FastAPI, uv | Асинхронный перевод одного фрагмента через локальную Ollama-модель |
| `trans-frontend` | PrimeReact, React, TypeScript | Реальный UI автоматического и ручного перевода |

Каждый сервис имеет собственные зависимости и может развиваться независимо. Python-зависимости зафиксированы в `uv.lock`; Java-зависимости управляются Maven Wrapper.

## Быстрые проверки

```bash
cd PDF-extractor && uv sync --dev
cd ../document-builder && uv sync --dev
cd ../trans-flow && uv sync --dev
cd ../trans-api && JAVA_HOME="$HOME/.local/share/jdks/temurin-21" ./mvnw test
```

Системные зависимости OCR (`tesseract-ocr`) устанавливаются отдельно от Python-пакетов. В репозиторий не следует добавлять модели, входные документы, сгенерированные PDF и секреты.
## Локальный запуск всего конвейера

Все сервисы собираются из собственных Dockerfile и запускаются одной командой.
Первый запуск скачивает локальную Ollama-модель и поэтому занимает больше времени.

```bash
cp .env.example .env
DOCKER_HOST=unix:///var/run/docker.sock docker compose up --build -d
DOCKER_HOST=unix:///var/run/docker.sock docker compose ps
```

После готовности контейнеров интерфейс доступен на
[http://localhost:8088](http://localhost:8088). Frontend обращается к
относительному `/api/v1`; Nginx направляет запросы в `trans-api`, а worker-сервисы
доступны только во внутренней сети Compose. Для остановки без удаления данных:

```bash
DOCKER_HOST=unix:///var/run/docker.sock docker compose down
```

Проверка декларативного контракта Compose выполняется командой
`./scripts/check-compose.sh`.
