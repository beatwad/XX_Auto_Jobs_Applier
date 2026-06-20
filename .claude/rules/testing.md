# Testing

## Framework

- `pytest` with `pytest-asyncio`, `pytest-mock`, `pytest-cov`.
- Config in `pytest.ini`: `testpaths=tests`, `pythonpath=. src`, `--cov=src --cov-report=term-missing`,
  `--strict-markers`, `-vv`.

## Running

```bash
pytest                                  # full suite (with coverage)
pytest tests/test_job_applier.py        # one file
pytest tests/test_utils.py::TestX::test_y   # one test
```

## Conventions

- Files: `test_*.py` / `*_test.py`; classes `Test*`; functions `test_*`.
- Markers must be **registered in `pytest.ini`** (`--strict-markers` rejects unknown ones).
  Current markers: `asyncio`, `authenticator`.
- Async tests use `@pytest.mark.asyncio` (Playwright/LLM code is async).
- Comments/docstrings follow the project rule — Russian (see @code-style.md).

## Fixtures & isolation (`tests/conftest.py`)

- Tests must **not** hit the network, real Telegram, or hh.ru — mock those boundaries.
- Autouse fixtures already: patch `AsyncTelegramSink` (no real messages), set mock env vars, and
  `setup_test_environment` creates/cleans `data_folder/*` dirs plus a throwaway `secrets.yaml`.
- For LLM code, construct `GPTAnswerer(..., test_mode=True)` or mock the chain to avoid real API calls.

## Notes

- Some existing tests are stale (`main.py` has a `# TODO: actualize tests`). When you touch a module,
  bring its tests back to green rather than assuming the suite is fully passing.
