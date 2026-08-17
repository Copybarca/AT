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

Прикладной код и endpoints пока отсутствуют. JDK 21 установлен отдельно от системной Java 17:

```bash
JAVA_HOME="$HOME/.local/share/jdks/temurin-21" ./mvnw test
```

## Database

По умолчанию сервис ожидает локальную PostgreSQL:

```text
jdbc:postgresql://localhost:5433/data
user=data
password=data
schema=trans
```

Для другого окружения используются переменные `DB_URL`, `DB_USER` и `DB_PASSWORD`.

## Docker

После добавления main-класса Spring Boot образ собирается и запускается так:

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
