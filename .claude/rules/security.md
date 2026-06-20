# Privacy & Security

- **Never log** passwords, API keys, tokens, or raw personal data. Mask before logging (existing
  code logs only the host part of a proxy, e.g. `proxy.split('@')[-1]`).
- **Secrets live in `data_folder/secrets/secrets.yaml`** (`hh_login`, `hh_password`, `llm_api_key`,
  `llm_proxy`, `tg_token`, `tg_api_id`, `tg_api_hash`) — **never commit it**. Template:
  `data_folder_example/secrets/secrets.yaml`. (`load_dotenv()` is called, but credentials come from
  the YAML, not `.env`.)
- **Anonymization** (`src/job_manager/resume_scraper.py`, gated by the `ANONYMIZE` config flag):
  - Personal data (name, contacts, github username, etc.) is replaced with dummy values from
    `DUMMY_PERSONAL_INFO_MALE` / `DUMMY_PERSONAL_INFO_FEMALE` in `src/constants.py` **before** the
    resume/text is sent to the LLM. City and birth date are intentionally **not** anonymized.
  - LLM **outputs** (cover letters, resume recommendations, contacts) are **de-anonymized** via
    `deanonymize_personal_information` before being used or shown.
  - Keep the anonymize → LLM → de-anonymize flow intact when editing LLM-facing code; don't leak
    raw personal data into prompts.
- **Validate only at system boundaries** — config files and LLM outputs (pydantic models in
  `src/views/`). Don't add redundant validation for already-validated internal data.
