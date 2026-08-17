# AT services

Монорепозиторий содержит четыре независимых backend-сервиса. На этом этапе созданы только каркасы, конфигурация сборки и зависимости; прикладной код и API endpoints отсутствуют.

| Сервис | Стек | Назначение |
| --- | --- | --- |
| `PDF-extractor` | Python 3.12, FastAPI, uv | Извлечение текста из текстовых и сканированных PDF |
| `document-builder` | Python 3.12, FastAPI, uv | Вёрстка книг и генерация PDF |
| `trans-api` | Java 21, Spring Boot, Maven | Внешний backend API перевода |
| `trans-flow` | Python 3.12, uv | Перевод через локальные LLM и агентные workflow |

Каждый сервис имеет собственные зависимости и может развиваться независимо. Python-зависимости зафиксированы в `uv.lock`; Java-зависимости управляются Maven Wrapper.

## Быстрые проверки

```bash
cd PDF-extractor && uv sync --dev
cd ../document-builder && uv sync --dev
cd ../trans-flow && uv sync --dev
cd ../trans-api && JAVA_HOME="$HOME/.local/share/jdks/temurin-21" ./mvnw test
```

Системные зависимости OCR (`tesseract-ocr`) устанавливаются отдельно от Python-пакетов. В репозиторий не следует добавлять модели, входные документы, сгенерированные PDF и секреты.
