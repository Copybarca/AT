# Translation Pipeline Runbook

Практический runbook для эксплуатации конвейера `PDF-extractor` → `trans-api` →
`trans-flow` → `document-builder`. Архитектурные требования и контракты находятся
в файле `dock`; этот документ описывает порядок действий и проверок.

## 1. Инварианты

Перед любыми операциями обязательны правила:

1. Только `trans-api` читает и изменяет постоянную БД и object storage.
2. Один `processId` обслуживается не более чем одним worker каждого типа.
3. Повтор команды с тем же `processId` безопасен.
4. Перевод относится к паре `stableKey + sourceHash`.
5. Принятый перевод не заменяется raw response модели.
6. Transport failure не создаёт review item.
7. Translation process завершается только при полном покрытии и пустой review
   queue.
8. Builder не публикует файл до независимой проверки PDF.
9. Секреты, книги и сгенерированные PDF не коммитятся в Git.

## 2. Предварительная проверка окружения

Перед сквозным запуском проверить:

- PostgreSQL и object storage доступны `trans-api`;
- Liquibase применил схемы `trans` и `scheduled-processes`;
- рабочие сервисы не имеют credentials БД и S3;
- health endpoints четырёх сервисов отвечают;
- inference endpoint загрузил требуемую модель;
- свободного места достаточно для original, assets, HTML и PDF;
- локальные очереди и worker pools имеют конечный размер;
- настроены timeout, retry backoff, lease TTL и лимит content attempts;
- версии extractor, validator, prompt и builder попадают в журналы.

## 3. Нормальный сквозной запуск

### 3.1. Загрузка

1. Отправить PDF и метаданные в `POST /api/v1/books`.
2. Получить `201 Created` и сохранить `bookId`.
3. Проверить существование original object и совпадение checksum.
4. Не запускать перевод, пока загрузка object не подтверждена.

### 3.2. Запуск перевода

1. Вызвать `POST /api/v1/books/{bookId}/translations`.
2. Получить `202 Accepted`.
3. Проверить одну строку extraction process со статусом `IN_PROGRESS`.
4. Убедиться, что повтор запроса не создаёт второй процесс.

### 3.3. Extraction

Наблюдать:

- accepted command и `processId` в extractor;
- checksum исходного PDF;
- технические batch uploads;
- отсутствие translation worker до final callback;
- совпадение заявленных и сохранённых counts.

Успешное завершение:

```text
storedTextPositions == manifestTextPositions
storedFigures == manifestFigures
storedFigureRegions == manifestFigureRegions
stableKeysAreUnique == true
sequentialNumbersAreContinuous == true
```

Только после этого extraction process получает `COMPLETED`.

### 3.4. Translation

Наблюдать:

- одну активную lease на processId;
- рост accepted positions;
- результаты attempts по причинам;
- размер review queue;
- inference latency;
- transport failures отдельно от validation failures.

Прогресс пересчитывается из фактических данных:

```text
acceptedPositions / totalTranslatablePositions
```

Если accepted count не меняется дольше двух максимальных inference timeout,
перейти к разделу диагностики.

### 3.5. Build

Перед командой builder проверить:

```text
acceptedPositions == totalTranslatablePositions
reviewQueueSize == 0
translationsForOldSourceHash == 0
```

Команда фиксирует profile, image policy, manifest checksum и expected counts.
После upload результата сравнить checksum и validation report.

## 4. Диагностические SQL-запросы

Имена таблиц адаптировать к итоговой Liquibase-схеме.

### 4.1. Фактический прогресс

```sql
SELECT
    count(*) AS total_positions,
    count(ts.original_text_hash) AS accepted_positions,
    count(*) - count(ts.original_text_hash) AS pending_positions,
    CASE WHEN count(*) = 0 THEN 0
         ELSE round(count(ts.original_text_hash) * 100.0 / count(*), 2)
    END AS percent
FROM trans.segment s
LEFT JOIN trans.translated_segment ts
       ON ts.original_text_hash = s.text_segment_hash
      AND ts.language = :target_language
WHERE s.book_id = :book_id
  AND s.text_segment_hash IS NOT NULL;
```

### 4.2. Позиции без принятого перевода

```sql
SELECT s.stable_key, s.sequential_number, s.text_segment_hash
FROM trans.segment s
LEFT JOIN trans.translated_segment ts
       ON ts.original_text_hash = s.text_segment_hash
      AND ts.language = :target_language
WHERE s.book_id = :book_id
  AND s.text_segment_hash IS NOT NULL
  AND ts.original_text_hash IS NULL
ORDER BY s.sequential_number;
```

### 4.3. Review queue

```sql
SELECT stable_key, source_hash, attempt_count, reason, updated_at
FROM trans.translation_review_item
WHERE book_id = :book_id
  AND target_language = :target_language
ORDER BY updated_at, stable_key;
```

### 4.4. Длительные процессы

```sql
SELECT id, book_id, status, started_at
FROM "scheduled-processes".translation_process
WHERE status = 'IN_PROGRESS'
  AND started_at < now() - interval '1 hour';
```

Возраст сам по себе не означает сбой: сравнить heartbeat/lease, последнюю attempt
и метрики dependency.

## 5. Дерево восстановления

### 5.1. Extraction остаётся `IN_PROGRESS`

1. Проверить доступность extractor.
2. Проверить final callback и manifest counts.
3. Если counts не совпадают, не запускать перевод.
4. Освободить истёкшую lease.
5. Повторить цельную extraction command с тем же processId.
6. Upsert batch должен восстановить данные без дубликатов.

### 5.2. Translation не продвигается

1. Проверить lease и исключить второй worker.
2. Найти последнюю attempt и текущий stable key.
3. Проверить inference health и timeout.
4. Для transport error восстановить dependency и повторить тот же ключ.
5. Для исчерпанных content strategies проверить один review item и продолжение
   следующих позиций.
6. Не очищать history attempts до выяснения причины.

### 5.3. Review queue не пуста

Для каждого элемента:

1. Сверить source text и `sourceHash` с текущей позицией.
2. Просмотреть raw responses и validation issues.
3. Выбрать полный кандидат либо подготовить ручной перевод.
4. Запустить тот же deterministic validator.
5. В одной транзакции сохранить accepted translation и удалить review item.
6. Сохранить provider `manual-review` и идентификатор ревизии.

Нельзя принимать ответ только потому, что он содержит целевой язык. Обязательно
проверить числа, RFC, URL, код, сноски и смысловую полноту.

### 5.4. Worker завершился после сетевого разрыва

1. Не менять уже принятые переводы.
2. Проверить, что последняя транзакция committed целиком либо отсутствует.
3. Убедиться, что старый worker не жив.
4. Получить новую lease.
5. Запустить reconciliation от фактически отсутствующих позиций.
6. Не использовать последнюю строку журнала как единственный checkpoint.

### 5.5. Builder завершился с ошибкой

1. Не публиковать частичный PDF.
2. Сохранить validation report и stderr browser process.
3. Проверить наличие manifest assets и доступность object URLs.
4. Проверить шрифты и browser version.
5. Повторить сборку целиком с тем же immutable manifest.
6. Загружать результат только при `validation.valid=true`.

## 6. Проверка чисел и литералов

До inference извлечь из source text обязательные токены:

- целые и десятичные числа;
- диапазоны с дефисом;
- даты и версии;
- IPv4/IPv6 и порты;
- URL/URI;
- RFC identifiers;
- code identifiers;
- footnote markers.

На первой и второй попытке сравнивать токены напрямую. На последней можно
применить protected placeholders:

```text
required = extractRequiredTokens(source)
protectedSource, mapping = replaceWithUniqueAlphabeticTokens(source, required)
raw = infer(protectedSource)
assert every required placeholder occurs exactly as expected
candidate = restoreExactOriginalTokens(raw, mapping)
validate(source, candidate)
```

Mapping существует только в памяти запроса и не переиспользуется между
фрагментами.

## 7. Приёмка ручного перевода

Чек-лист одного review item:

- stable key и source hash актуальны;
- технический термин согласован с glossary;
- смысл каждой исходной фразы присутствует;
- числа и диапазоны совпадают посимвольно;
- RFC, OAuth/OIDC/JWT names и identifiers сохранены;
- URL не локализованы и не исправлены без правила;
- код не переведён;
- списки и индексные строки не потеряли элементы;
- validator возвращает пустой список issues;
- accepted translation и удаление queue item происходят одной транзакцией.

## 8. Build profiles

### `CLEAN`

- только книжный текст и изображения;
- stable keys отсутствуют;
- служебные статусы и OCR placeholders не выводятся.

### `REVIEW_KEYS`

- перед каждым текстовым, кодовым и графическим элементом выводится stable key;
- ключ компактный и не перекрывает содержимое;
- текст и изображения идентичны clean build.

### Image policy

`KEEP_ORIGINAL_ARTWORK` сохраняет изображение целиком. Непереведённые OCR
regions не блокируют build и не выводятся отдельным текстом.

`LOCALIZE_TEXT_REGIONS` требует явного правила для отсутствующего перевода.
Нельзя молча стирать английскую область без принятого целевого текста.

## 9. PDF validation gate

Публикация разрешена, только если:

```text
pdfReadable == true
encryptedUnexpectedly == false
pageCount > 0
pageSizes == expected
unexpectedBlankPages == 0
missingTextMarkers == 0
figureInstances == expectedFigures
firstControlTextPresent == true
lastControlTextPresent == true
cleanStableKeys == 0                  # CLEAN
reviewStableKeys > 0                  # REVIEW_KEYS
sha256Calculated == true
```

Визуальный smoke test:

1. Обложка.
2. Оглавление.
3. Обычная страница.
4. Заголовок у нижней границы.
5. Код.
6. Рисунок.
7. Предметный указатель.
8. Последняя страница.

## 10. Метрики и алерты

Рекомендуемые алерты:

- `IN_PROGRESS` без attempt и heartbeat дольше двух timeout;
- lease старше TTL;
- два worker для одного processId;
- transport failure rate выше порога;
- review queue непрерывно растёт;
- accepted count больше total count;
- builder figure count не совпадает с manifest;
- PDF validation failure;
- нехватка диска перед extraction или build.

Алерт не создаёт новый бизнес-статус. Он инициирует диагностику и безопасный
повтор атомарной команды.

## 11. Критерии завершения

Extraction:

```text
status == COMPLETED
manifest counts == stored counts
stable keys unique
reading order continuous
```

Translation:

```text
status == COMPLETED
accepted positions == total positions
review queue == 0
old source hash matches == 0
```

Build:

```text
status == COMPLETED
object exists
checksum matches
validation valid
book.translated_path points to final object
```

## 12. Безопасная очистка временных данных

Очистку выполнять после подтверждения checksum опубликованного результата и
сохранения audit history.

1. Получить точный список временных путей processId.
2. Проверить real path, владельца и отсутствие открытых файлов.
3. Не использовать широкие glob по общим каталогам.
4. Удалить browser profile, temporary HTML, raster previews и local copies.
5. Завершить только tunnel/model process конкретной задачи.
6. Не удалять общие модели, системные журналы и данные других книг.
7. Проверить отсутствие listener и временных путей.

Retention для attempts, review history и validation reports задаётся отдельно:
эти данные полезны для качества, расследований и регрессий.

## 13. Регрессионный сценарий полной книги

Кроме маленьких fixture хранить лицензированно допустимый крупный профиль:

```text
300–400 physical pages
2500–3500 text positions
100–200 figures
1000+ OCR regions
несколько намеренно дефектных model responses
один искусственный transport disconnect
```

Проверить:

- безопасное возобновление после disconnect;
- продолжение после content review exception;
- точный прогресс по позициям;
- полное покрытие stable keys;
- clean и review PDF;
- одинаковое число рисунков в обоих profiles;
- отсутствие пустых страниц и незавершённых текстовых маркеров.
