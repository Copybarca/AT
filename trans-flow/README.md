# trans-flow

Каркас Python-сервиса для локальных LLM-пайплайнов перевода:

- `Transformers`, `Torch`, `Accelerate`, `SentencePiece`, `safetensors` — локальный inference;
- `Hugging Face Hub` — получение моделей;
- `LangChain`, `LangGraph`, `langchain-ollama` — агенты и workflow;
- `Ollama` — локальный модельный backend;
- `lingua-language-detector`, `sentence-splitter` — определение языка и сегментация;
- `sacrebleu` — оценка качества перевода.

Дополнительные backends подключаются extras:

```bash
uv sync --dev
uv sync --extra llama-cpp
uv sync --extra quantization
```

Модели в Git не хранятся. Прикладной код пока отсутствует.
