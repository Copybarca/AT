# trans-api

Каркас Java backend API:

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
| `POST` | `/api/v1/books` | Создать книгу |
| `PATCH` | `/api/v1/books/{bookId}` | Обновить title/originalLanguage |
| `DELETE` | `/api/v1/books/{bookId}` | Удалить книгу |
| `POST` | `/api/v1/books/{bookId}/original` | Загрузить оригинал любого формата в S3 |
| `POST` | `/api/v1/books/{bookId}/translated` | Загрузить переведённый PDF в S3 |

Архитектурные пакеты: `controller`, `dto`, `service`, `repo`, `restclient`. Внешние клиенты возвращают `Optional<?>`, пока контракты ответов соседних сервисов не определены.

## Database

По умолчанию сервис ожидает локальную PostgreSQL:

```text
jdbc:postgresql://localhost:5433/data
user=data
password=data
schema=trans
```

Для другого окружения используются переменные `DB_URL`, `DB_USER` и `DB_PASSWORD`.

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
