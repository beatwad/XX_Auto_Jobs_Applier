# Environment

- **Manager**: [uv](https://docs.astral.sh/uv/). Dependencies and Python version are declared in
  `pyproject.toml` (`requires-python = ">=3.12"`).
- **Virtual environment**: `.venv/` at the repo root, created/updated by `uv sync` (uv fetches the
  right Python 3.12 itself).

Run project commands through uv so they use `.venv`:

```bash
uv sync                  # create/update the env from pyproject.toml (incl. dev group)
uv run python main.py    # run the app
uv run pytest            # run the tests
uv add <package>         # add a dependency (updates pyproject.toml + uv.lock)
```

Don't call a global/conda `python` or `pip` directly — prefer `uv run` / `uv add`.

## Key Libraries

| Library | Purpose |
|---------|---------|
| `playwright` | Browser automation |
| `langchain`, `langchain-core`, `langchain-community` | LLM orchestration |
| `langchain-google-genai`, `langchain_openai` | LLM providers (Gemini, OpenAI) |
| `loguru` | Logging |
| `httpx` | HTTP client |
| `PyYAML` | YAML config parsing |
| `jsonschema` | JSON validation |
| `telethon`, `python-telegram-bot` | Telegram integration |
| `Levenshtein` | String similarity |
| `pytest`, `pytest-asyncio`, `pytest-mock`, `pytest-cov` | Testing |
