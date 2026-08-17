# PDF-extractor

Каркас Python/FastAPI-сервиса для извлечения текста:

- `pypdf`, `PyMuPDF`, `pdfplumber` — текстовый слой и структура PDF;
- `OCRmyPDF`, `pytesseract`, `pdf2image`, `Pillow` — сканы и изображения;
- `FastAPI`, `Uvicorn`, `python-multipart` — будущий HTTP API и загрузка файлов;
- `pydantic-settings` — конфигурация окружения.

Прикладной код пока отсутствует. Для OCR кроме Python-зависимостей потребуются системные `tesseract-ocr` и языковые пакеты Tesseract; `pdf2image` использует Poppler.

```bash
uv sync --dev
```
