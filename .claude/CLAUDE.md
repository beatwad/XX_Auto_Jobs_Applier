# XX Auto Jobs Applier — Project Guide

## Rules

- @rules/environment.md — Python interpreter, conda env, key libraries.
- @rules/code-style.md — language (Russian comments/logs), typing, naming, error handling, async.
- @rules/configuration.md — config files, runtime source of truth, flags, validation.
- @rules/testing.md — pytest setup, markers, fixtures, isolation.
- @rules/llm.md — `GPTAnswerer` usage, prompts, providers, cost logging, privacy.
- @rules/security.md — secrets handling, anonymization flow, logging hygiene.


AI-assisted tool that automates job search and applications on **hh.ru**. It finds vacancies,
scores their relevance with an LLM, and applies with personalized cover letters and answers to
employer questions. Originally a fork of AIHawk.

**Important:** hh.ru closed its public API for job seekers, so the app now drives the site through
browser emulation (Playwright) using the user's login/password.

## Tech Stack

- **Python 3.12** (target `py312`). Async throughout (`asyncio`).
- **Playwright** — browser automation (auth, application flow, scraping).
- **LangChain** — LLM access: OpenAI, Google Gemini, Claude, GigaChat, Ollama, HuggingFace.
- **pydantic** — config/data validation (see `src/views/`).
- **PyYAML** — config and output files.
- **loguru** — logging.
- **telethon** / **python-telegram-bot** — Telegram notifications & CAPTCHA relay.

## Running

Dependencies are managed with **uv** (`pyproject.toml`). `uv sync` creates `.venv` and installs
everything; `uv run ...` runs commands inside it.

```bash
uv sync                       # set up / update the env (fetches Python 3.12, installs deps + dev group)
uv run python main.py         # entry point: validates config, runs the bot once
```

Requires `data_folder/secrets/secrets.yaml` and `data_folder/search_config/search_config.yaml`
(see `data_folder_example/` for templates). On first run a browser may need a manual CAPTCHA;
session state is persisted under `chrome_profile/` / `data_folder/browser_session/`.

## Tests

```bash
uv run pytest                 # config in pytest.ini: --cov=src, strict markers, testpaths=tests
```

- `pytest-asyncio` is used; async tests need the `asyncio` marker.
- Tests live in `tests/`, named `test_*.py`. There are known stale tests (see `main.py` TODOs).

## Architecture (`src/`)

- **Entry point**: `main.py` — `ConfigValidator` + `FileManager` validate config, then
  `create_and_run_bot` wires components and runs `BotFacade`.
- **`job_manager/`** — core flow:
  - `playwright_manager.py` — Playwright instance, hh.ru auth, high-level site interactions.
  - `bot_facade.py` — orchestrates resume scraper, search customizer, job applier.
  - `job_applier.py` — find vacancies, decide, apply, handle question/CAPTCHA scenarios.
  - `resume_scraper.py` — fetch & parse the user's resume from hh.ru.
  - `search_customizer.py` — turn search params into hh.ru filters.
- **`llm/`** — `llm_manager.py` (`GPTAnswerer`, provider interface) and `prompts.py` (templates:
  `job_is_interesting`, `coverletter_template`, `fixed_cover_letter`).
- **`views/`** — pydantic models: `config.py` (`SearchConfig`, `Secrets`), `job.py`, `llm.py`, `resume.py`.
- **`telegram/`** — notifications, async error sink, CAPTCHA relay, chat/topic id helper.
- **`resume_builder/`** — (experimental) HTML/CSS resume generation.
- **`utils/`** — browser helpers, file ops, text sanitization.
- **`constants.py`** — paths (`SECRETS_FILE`, `SEARCH_CONFIG_FILE`), dummy anonymization data, LLM prices.
- **`logger_config.py`** — loguru setup.

## Configuration

Three YAML files under `data_folder/` (secrets, search config, app config). Runtime settings are
loaded from `data_folder/app_config/app_config.yaml` via `load_app_config()` — **not** from
`src/app_config.py`. See @rules/configuration.md for files, flags, and validation.

## Output (`data_folder/output/`)

`answers.yaml` (cached LLM Q&A), `success.yaml`, `skipped.yaml`, `failed.yaml`, `resume.yaml`,
`cover_letters.txt`, `skill_stat.yaml`.
