# Configuration

Three YAML files drive the app. Paths are defined in `src/constants.py`; templates live in
`data_folder_example/`. Copy a template into `data_folder/` and fill it in.

| File (`src/constants.py` const) | Path | Purpose |
|---|---|---|
| `SECRETS_FILE` | `data_folder/secrets/secrets.yaml` | Credentials & API keys — **never commit** |
| `SEARCH_CONFIG_FILE` | `data_folder/search_config/search_config.yaml` | hh.ru search parameters |
| `APP_CONFIG_FILE` | `data_folder/app_config/app_config.yaml` | Runtime behavior flags |

## Loading config — source of truth

- Read runtime settings via `load_app_config()` from `src/utils/utils.py`, then
  `config.get("KEY", default)`. **Do not hardcode** model names, modes, or thresholds elsewhere.
- The **runtime** source of truth is `data_folder/app_config/app_config.yaml`, **not**
  `src/app_config.py`. `src/app_config.py` mirrors the same constants but is not what the running
  app loads. When the README / `.cursor/rules` / `src/app_config.py` disagree with the YAML, the
  YAML wins.

## `app_config.yaml` keys

- `ANONYMIZE` — anonymize personal data in resume/cover letters before sending to the LLM.
- `MONKEY_MODE` — apply to every found vacancy, skipping LLM interest filtering.
- `SEARCH_MODE` — don't apply; only save generated cover letters/job descriptions.
- `SKILL_STAT_MODE` — don't apply; collect in-demand skill stats to `data_folder/output/skill_stat.yaml`.
- `JOB_IS_INTERESTING_THRESH` — LLM interest score (1–100) cutoff for applying (default 70).
- `RAISE_RESUME` — bump the resume in search results on startup (max once / 4h).
- `HEADLESS_MODE` — run the browser headless.
- `MINIMUM_WAIT_TIME_SEC` — minimum time spent per application.
- `MINIMUM_LOG_LEVEL` — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`.
- `LLM_MODEL_TYPE`, `LLM_MODEL`, `TEMPERATURE` — LLM provider, model, sampling temperature.

## `search_config.yaml` — key fields

- `job_title` — must **exactly** match a resume title on hh.ru.
- `job_blacklist` — companies to skip.
- `cover_letter` — if non-empty, used verbatim for all vacancies; otherwise one is generated per job.
- Other fields mirror hh.ru search filters.

## Validation

- `secrets.yaml` and `search_config.yaml` are validated at startup by `ConfigValidator` in `main.py`
  against the pydantic models `Secrets` and `SearchConfig` in `src/views/config.py`.
- Invalid/missing config raises `ConfigError`. When adding a config field, update the matching
  pydantic model.
