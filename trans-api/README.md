# trans-api

Java backend API, владелец PostgreSQL/S3 и оркестратор PDF pipeline:

- Java 21;
- Spring Boot 4.0.7;
- Spring MVC;
- Bean Validation;
- Spring Boot Actuator;
- Spring Data JPA;
- PostgreSQL JDBC;
- Maven Wrapper 3.9.16.

JDK 21 установлен отдельно от системной Java 17:

```bash
JAVA_HOME="$HOME/.local/share/jdks/temurin-21" ./mvnw test
```

## API книг

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `POST` | `/api/v1/books` | Одной multipart-операцией создать книгу и сохранить PDF |
| `PATCH` | `/api/v1/books/{bookId}` | Обновить title/originalLanguage |
| `DELETE` | `/api/v1/books/{bookId}` | Удалить книгу |
| `POST` | `/api/v1/books/{bookId}/original` | Загрузить оригинал любого формата в S3 |
| `POST` | `/api/v1/books/{bookId}/translated` | Загрузить переведённый PDF в S3 |

Архитектурные пакеты: `controller`, `dto`, `service`, `repo`, `model`, `restclient`. Пакет `model` содержит JPA-сущности схем `trans` и `scheduled-processes`.

## Pipeline API

- `POST /api/v1/books/{bookId}/translations` — идемпотентно запускает extraction → translation → build и возвращает 202;
- `GET /api/v1/books/{bookId}/processes?targetLanguage=ru` — возвращает два состояния и вычисляемый процент перевода;
- `/internal/v1/books/{bookId}/extraction/*` — idempotent batch/image/region/complete callbacks extractor;
- `POST /internal/v1/books/{bookId}/build-result` — raw validated `application/pdf` callback builder.

Внешние клиенты типизированы. Все внутренние вызовы используют
`INTERNAL_SERVICE_TOKEN`. Один `PipelineTaskQueue` владеет bounded local queue;
после рестарта `PipelineRecoveryService` восстанавливает `IN_PROGRESS` jobs из
PostgreSQL.

## Локальная проверка

```bash
JAVA_HOME="$HOME/.local/share/jdks/temurin-21" ./mvnw test
RUN_DB_TESTS=true \
  JAVA_HOME="$HOME/.local/share/jdks/temurin-21" \
  ./mvnw test
```

Вторая команда ожидает только локальные PostgreSQL на `localhost:5434` и MinIO
на `localhost:9000`, которые поднимаются через `compose.yaml`. Модель перевода
в тестах не запускается.


## Database

По умолчанию сервис ожидает локальную PostgreSQL:

```text
jdbc:postgresql://localhost:5433/data
user=data
password=data
schema=trans
```

Для другого окружения используются переменные `DB_URL`, `DB_USER` и `DB_PASSWORD`.

Схема `trans` создаётся и обновляется Liquibase при старте приложения. Cumulative migration находится в `src/main/resources/db/changelog/cumulative/db.changelog-cumulative.sql`; JPA только валидирует готовую схему.

Настройки S3 и внешних REST API находятся в `application.yaml` и переопределяются environment variables. Для S3-совместимого хранилища доступны `S3_ENDPOINT` и `S3_PATH_STYLE_ACCESS`.

## Docker

Образ собирается и запускается так:

```bash
docker build -t trans-api .
docker run --rm \
  --name trans-api \
  --add-host host.docker.internal:host-gateway \
  -p 8080:8080 \
  -e DB_URL=jdbc:postgresql://host.docker.internal:5433/data \
  -e DB_USER=data \
  -e DB_PASSWORD=data \
  trans-api
```

## Docker Compose

`compose.yaml` поднимает отдельный локальный стек без конфликта с PostgreSQL на `5433`. PostgreSQL стартует пустым, а схему создаёт Liquibase из `trans-api`:

- `trans-api` — `127.0.0.1:8080`;
- PostgreSQL — `127.0.0.1:5434`;
- MinIO S3 API — `127.0.0.1:9000`;
- MinIO Console — `127.0.0.1:9001`.

```bash
docker compose up --build -d
docker compose ps
```

Все значения имеют локальные defaults и переопределяются environment variables. URL внешних сервисов задаются через `PDF_EXTRACTOR_BASE_URL`, `PDF_BUILDER_BASE_URL` и `AGENT_FLOW_BASE_URL`.
