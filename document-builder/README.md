# document-builder

Каркас Python/FastAPI-сервиса для сборки книг и документов:

- `WeasyPrint`, `Jinja2`, `Markdown` — HTML/CSS-шаблоны и печатная вёрстка;
- `ReportLab` — программное создание PDF;
- `PyPDF` — сборка, метаданные и постобработка PDF;
- `CairoSVG`, `Pillow`, `fonttools` — графика, изображения и шрифты;
- `Babel` — локализация;
- `FastAPI`, `Uvicorn`, `python-multipart` — будущий HTTP API.

Прикладной код пока отсутствует.

```bash
uv sync --dev
```
