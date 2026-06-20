# Code Style (`**/*.py`)

## Language for Comments and Logs

- **All** comments, docstrings and `logger.*()` messages must be written **in Russian only**.
- Applies to inline comments, class/method docstrings, and any string passed to the logger.

```python
# ❌ Bad
logger.info("Initializing JobApplier")
# Load config from file

# ✅ Good
logger.info("Инициализация JobApplier")
# Загрузка конфига из файла
```

## Python

- **Python 3.12+** — use matching syntax and features.
- Type annotations are required for function/method arguments and return values.
- Use `pydantic` for data validation and models.
- Logging via `loguru`: `from src.logger_config import logger`.
- Import order: standard library → third-party packages → internal modules, separated by blank lines.
- Formatting: **black** and **isort** (black profile), line length **100**.

## Naming

- Classes: `PascalCase`
- Functions, methods, variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private attributes/methods: `_` prefix

## Class Structure

- Class docstring in Russian — a single line describing the purpose.
- Methods get a docstring when the logic is non-obvious.

```python
class JobApplier:
    """Поиск и рассылка откликов работодателям."""

    async def apply(self, job: Job) -> bool:
        """Отправляет отклик на вакансию. Возвращает True при успехе."""
        ...
```

## Error Handling

- Catch specific exceptions (use traceback when needed); avoid a bare `except Exception` that swallows errors.
- Log errors with context via `logger.error()` or `logger.exception()`.

```python
# ❌ Bad
except Exception:
    pass

# ✅ Good
except PlaywrightTimeoutError as e:
    logger.error(f"Таймаут при загрузке страницы вакансии: {e}")
except Exception:
    tb_str = traceback.format_exc()
    logger.error(f"Неизвестная ошибка\n{tb_str}")
```

## Async

- Async code uses `async/await` (Playwright is always async).
- Do not block the event loop with synchronous calls inside async functions.
