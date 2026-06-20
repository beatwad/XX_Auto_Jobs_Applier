# LLM Integration

Entry point: `GPTAnswerer` in `src/llm/llm_manager.py`. Model type, model name, and temperature are
read **globally** from the app config (`load_app_config()`), not passed per call.

```python
from src.llm.llm_manager import GPTAnswerer

gpt = GPTAnswerer(llm_api_key, llm_proxy)        # test_mode=True short-circuits live calls
gpt.set_resume(structured_resume, resume_readable)  # set context before asking
gpt.set_job(job)
gpt.set_search_parameters(parameters)
score = gpt.job_is_interesting()                 # -> {"score": int, "reasoning": str}
letter = gpt.write_cover_letter()
```

## Rules

- **All prompts live in `src/llm/prompts.py`** — never inline a prompt anywhere else. Chains are
  built once in `GPTAnswerer.__init__` via `_create_chain` / `_create_pydantic_chain`.
- **Set context first**: call `set_resume` / `set_job` / `set_search_parameters` before any
  question/letter method that depends on it.
- **Structured outputs** use pydantic models in `src/views/llm.py` (`JobIsInteresting`,
  `ResumeIsInteresting`, `ContactInfo`) via `PydanticOutputParser`; pass
  `parser.get_format_instructions()` into the prompt. Add new structured shapes there.
- **Validate / guard LLM responses.** LLM-call methods catch failures and return safe defaults
  (e.g. `{"score": 0, ...}`) instead of raising; `find_best_match` (Levenshtein) snaps free-text
  answers back onto the allowed options. Keep this defensive pattern.
- **Privacy**: prompts must use anonymized data; don't leak raw personal data. See @security.md.

## Providers

- `AIAdapter` currently supports `"openai"`, `"openrouter"` and `"gemini"`. `openrouter` reuses
  `langchain_openai.ChatOpenAI` pointed at `https://openrouter.ai/api/v1`, so any model on
  OpenRouter is addressed by its slug (e.g. `anthropic/claude-sonnet-4-6`). `claude`, `ollama`,
  `huggingface`, `gigachat` exist as **commented-out** classes — to enable one, uncomment its
  `AIModel` subclass and its branch in `AIAdapter._create_model`.
- **Adding a provider**: subclass `AIModel` and implement only `_build_model(llm_proxy)` — it returns
  the provider's chat client for a single proxy (or `None`). The base `AIModel.invoke` handles
  prompt assembly and proxy failover; don't override it.
- **Proxy failover**: `llm_proxy` is a `List[str]` (`Secrets.llm_proxy`). On every call, `AIModel.invoke`
  shuffles the list and tries proxies one by one, rebuilding the client per proxy, until a request
  succeeds; if all fail it re-raises the last error. An empty list means "no proxy". Proxies are
  masked to host-only in logs (`proxy.split('@')[-1]`).

## Cost & logging

- Every call is logged by `LLMLogger.log_request` to `data_folder/output/llm_api_calls.yaml`
  (prompts, token usage, computed cost).
- Cost comes from `PRICE_DICT` in `src/constants.py`. **When adding a new model, add its
  per-token price there** or cost falls back to a default estimate.
- `LoggerChatModel` retries on HTTP 429, honoring `retry-after` / `retry-after-ms` headers.
