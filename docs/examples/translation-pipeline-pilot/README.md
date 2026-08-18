# Translation pipeline pilot: reference implementation

Этот каталог содержит код, который использовался при полном переводе и сборке
технической книги. Он сохранён как reference implementation для переноса
проверенных алгоритмов в сервисы AT.

Это не альтернативная production-архитектура: постоянные данные пилота хранились
в SQLite, а в AT ими должен владеть `trans-api` через PostgreSQL и внутренние
HTTP-контракты, описанные в `../../../dock`.

## Состав

| Файл | Назначение |
| --- | --- |
| `translate_memory_translategemma.py` | Однофрагментный worker, retries, validation, attempts и review queue |
| `translate_memory.py` | Минимальный support adapter для SQLite и TSV-глоссария |
| `translate_memory_local.py` | Консервативное распознавание сохраняемых литералов |
| `export_markdown_manuscript.py` | Экспорт memory в общий и постраничный Markdown |
| `build_reflow_html.py` | Восстановление порядка, классификация блоков и потоковый HTML |
| `glossary.example.tsv` | Реальный пример формата предметного глоссария |
| `tests/test_translate_memory_translategemma.py` | 7 unit-тестов retry/persistence core |
| `design/` | Спецификация, план реализации и правила PDF-вёрстки пилота |

## Что проверено реальным прогоном

- worker обработал все 2964 текстовые позиции;
- после transport disconnect повторный запуск пропустил готовые ключи и дошёл до
  конца;
- content failures отдельных фрагментов не остановили книгу;
- 19 исчерпанных фрагментов сохранились в review queue;
- после ручного принятия очередь стала пустой;
- Markdown exporter сформировал 377 постраничных файлов;
- reflow builder включил 146 оригинальных изображений;
- были собраны clean PDF и review PDF с ключами;
- в каждом результате отсутствовали неожиданные пустые страницы и маркеры
  незавершённого книжного текста.

## Важная оговорка о support-модулях

Точный worker пилота импортировал два orchestration-модуля рабочего каталога.
Они не входили в сохранённый bundle после завершения пилота. Файлы
`translate_memory.py` и `translate_memory_local.py` в этом каталоге являются
маленькими совместимыми adapters:

- предоставляют тот же импортируемый API;
- не содержат бизнес-оркестрацию AT;
- позволяют импортировать worker и запускать сохранённые unit-тесты;
- делают CLI пригодным для локального эксперимента с совместимой SQLite-базой.

Основной алгоритм `translate_memory_translategemma.py`, тесты, exporter и builder
скопированы из фактически использованной версии.

## Быстрая проверка

Из этого каталога:

```bash
python3 -m py_compile \
  translate_memory.py \
  translate_memory_local.py \
  translate_memory_translategemma.py \
  export_markdown_manuscript.py \
  build_reflow_html.py

python3 -m unittest discover -s tests -v
```

Для проверки builder установить зависимость:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m py_compile build_reflow_html.py
```

Headless Chrome является внешней runtime-зависимостью финальной печати PDF и не
устанавливается этим example bundle.

## Локальный запуск translator worker

Worker ожидает SQLite-базу с таблицей `segments` и использует следующие
переменные:

```text
TRANSLATION_MEMORY_DB=/path/to/translation_memory.sqlite3
TRANSLATION_GLOSSARY=/path/to/glossary.tsv
```

Endpoint и модель в сохранённом прототипе:

```text
http://127.0.0.1:11435/api/generate
translategemma:12b
```

Это исторические defaults пилота. В production `trans-flow` должен получать
конфигурацию через ENV/application settings, а не использовать эти константы.

Пример локальной команды после подготовки совместимой базы и endpoint:

```bash
TRANSLATION_MEMORY_DB=/path/to/translation_memory.sqlite3 \
TRANSLATION_GLOSSARY=./glossary.example.tsv \
python3 translate_memory_translategemma.py --start 1
```

Скрипт:

1. создаёт служебные таблицы attempts/drafts/review queue при отсутствии;
2. пропускает принятые версии `stableKey + sourceHash`;
3. применяет точный glossary/preserve rule;
4. выполняет до трёх content strategies;
5. сохраняет каждую попытку;
6. принимает прошедший validation ответ либо создаёт review item;
7. продолжает следующий фрагмент;
8. прекращает работу при transport failure.

## Markdown exporter

`export_markdown_manuscript.py` ожидает рядом совместимую
`translation_memory.sqlite3`. Он экспортирует:

```text
manuscript/source/book.md
manuscript/source/pages/page-NNNN.md
manuscript/bilingual/book.md
manuscript/bilingual/pages/page-NNNN.md
```

В production exporter должен получать manifest через API, но формат удобен для
отладки stable keys, source text, translation, bbox и figure references.

## Reflow builder

Пример построения HTML:

```bash
python3 build_reflow_html.py \
  --markdown manuscript/bilingual/book.md \
  --source-pdf source.pdf \
  --asset-root /portable/project/root \
  --end-page 390 \
  --output book-clean.html
```

Review-вариант:

```bash
python3 build_reflow_html.py \
  --markdown manuscript/bilingual/book.md \
  --source-pdf source.pdf \
  --asset-root /portable/project/root \
  --end-page 390 \
  --show-keys \
  --output book-review-keys.html
```

Builder:

- восстанавливает порядок по page/bbox/key;
- классифицирует заголовки, body, lists, notes, captions и code;
- повторно вставляет исключённые из translation memory code blocks;
- соединяет абзацы, разделённые физической страницей;
- вставляет оригинальные figures;
- формирует HTML/CSS для потоковой книжной вёрстки.

Собственно печать HTML в PDF выполняется внешним browser process. После печати
PDF требуется validation gate из `../../../TRANSLATION_PIPELINE_RUNBOOK.md`.

## Что намеренно не включено

- исходная и переведённая книга;
- SQLite backup с содержимым книги;
- модели Ollama;
- raw runtime logs;
- machine-specific paths и IP;
- одноразовая таблица из 19 ручных переводов;
- browser profiles и сгенерированные PDF.

Эти данные не нужны для разработки сервисов и не должны попадать в Git.

## Как переносить в AT

- pure validation/protection functions → библиотека или domain service
  `trans-api`;
- HTTP inference call → клиент `trans-api` к stateless `trans-flow`;
- attempts и review queue → PostgreSQL entities/repositories `trans-api`;
- glossary selection → translation application service;
- Markdown export → diagnostic tooling, не основной interservice contract;
- ordering/classification/reflow → `document-builder`;
- PyMuPDF extraction profile → `PDF-extractor`/`document-builder` в зависимости
  от операции;
- browser print и PDF validation → `document-builder`;
- unit-тесты из bundle → исходная база для портированных service tests.

Не переносить SQLite connection, локальные пути и fixed endpoint как production
решения.
