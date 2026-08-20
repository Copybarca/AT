# Сквозной PDF-конвейер: проектирование

Дата: 2026-08-20
Статус: утверждено пользователем

## Цель

Пользователь загружает английский PDF во frontend, выбирает целевой язык и одним
действием запускает сохранение оригинала, extraction, перевод всех фрагментов и
автоматическую сборку итогового PDF. UI показывает только фактические состояния
backend; готовый PDF можно скачать, переводы — проверить и изменить вручную.

## Граница системы

В Compose входят frontend, nginx, trans-api, pdf-extractor, trans-flow,
document-builder, PostgreSQL, MinIO и Ollama. Только Nginx публикуется для
пользовательского трафика. PostgreSQL и MinIO доступны только trans-api, а
worker-сервисы общаются с API через авторизованные internal callbacks.

Nginx отдаёт SPA по / и проксирует /api/ в trans-api. Локальный адрес по
умолчанию — http://localhost:8088; необязательное имя at.local документируется,
но не требуется для запуска.

## Публичный API

Все пользовательские ручки принадлежат trans-api и имеют префикс /api/v1.
Frontend никогда не вызывает worker-сервисы, storage или Ollama напрямую.

### Книги и pipeline

- POST /api/v1/books принимает multipart file, title и originalLanguage.
- POST /api/v1/books/{bookId}/translations принимает targetLanguage и
  идемпотентно запускает либо продолжает extraction → translation → build.
- GET /api/v1/books принимает search/status и возвращает items плюс счётчики.
- GET /api/v1/books/{bookId} возвращает карточку книги.
- GET /api/v1/books/{bookId}/processes?targetLanguage=... возвращает стадии.
- GET /api/v1/books/{bookId}/translated?targetLanguage=... скачивает готовый PDF.

Frontend после создания книги сразу вызывает translations. Если запуск не принят,
книга остаётся сохранённой, UI показывает ошибку и разрешает безопасный повтор.

### DTO книги

DTO содержит id, title, fileName, sourceLanguage, targetLanguage, contentStatus,
translationStatus, pdfStatus, totalFragments, translatedFragments, imageCount и
updatedAt. Статусы вычисляет backend из process-таблиц и фактических данных.
Текущая версия хранит один выбранный targetLanguage на книге, что соответствует
существующему единственному translatedPath.

### Фрагменты и ручной перевод

- GET /api/v1/books/{bookId}/fragments использует targetLanguage, filter
  all|untranslated, afterSequence и limit; порядок строго sequentialNumber.
- PUT /api/v1/books/{bookId}/fragments/{fragmentId}/translation принимает
  targetLanguage и непустой translatedText.

Ручное изменение перевода инвалидирует готовую сборку. Отдельная таблица
UI-состояния не создаётся: источники истины — segments, translations и processes.

### Сборка

- POST /api/v1/books/{bookId}/build принимает targetLanguage и replaceExisting.
- Сборка запрещена до завершения extraction и translation.
- Для готового PDF требуется replaceExisting=true.
- Нормальный pipeline автоматически начинает build после полного перевода.

## Frontend

Demo adapter работает только при явном VITE_DEMO_MODE=true. Production-сборка
не может молча имитировать успех. В Compose frontend использует относительный
/api/v1 через Nginx, а multipart-поля и DTO совпадают с backend.

После загрузки выполняется переход в список документов. До появления websocket
список и карточка используют ограниченный polling и сохраняют ручное обновление.

## Контейнеризация

Каждый прикладной пакет имеет Dockerfile на стандартном Linux-образе:

- trans-api: Maven/Temurin 21 build stage и Temurin 21 JRE runtime;
- Python-сервисы: Python 3.12 slim и зависимости из uv.lock;
- frontend: Node.js 22 Alpine build stage и Nginx Alpine runtime;
- gateway: официальный Nginx Alpine с репозиторным конфигом.

Корневой compose.yaml содержит build contexts, внутреннюю сеть, volumes,
healthchecks, конечные очереди и безопасные локальные defaults. Корневой
.env.example документирует параметры. ollama-init ждёт Ollama и загружает
настраиваемую модель; default сохраняется qwen3:8b.

## Ошибки и восстановление

Каждая стадия хранит IN_PROGRESS, COMPLETED или FAILED. Повтор запуска продолжает
работу с отсутствующего результата. Переполнение очереди наблюдаемо. UI различает
ошибки upload, extraction, translation и build. Невалидный PDF не публикуется.

## Проверка

1. Backend tests фиксируют DTO, фильтры, cursor pagination, ручной перевод,
   build guards и скачивание.
2. Frontend tests фиксируют multipart-контракт, create/start, явный demo и polling.
3. Unit tests всех backend-пакетов проходят.
4. docker compose config и сборка всех образов проходят с чистого checkout.
5. E2E загружает PDF через Nginx, ждёт три COMPLETED, скачивает и проверяет PDF.
6. Финальный прогон использует копию двух страниц английской книги с рабочего
   стола. Исходник не меняется; артефакты лежат в игнорируемой .e2e-work.

## Критерий готовности

После запуска одной Compose-командой и открытия http://localhost:8088 пользователь
загружает двухстраничный английский PDF, выбирает русский язык и без дополнительных
операций получает скачиваемый валидный PDF после завершения всех стадий.
