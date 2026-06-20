# Личные данные-пустышки для анонимизации (мужской пол)
DUMMY_PERSONAL_INFO_MALE = {
    "first_name": "Аристаний",
    "first_name_2": "Ари́станий",
    "first_name_3": "Ариста́ний",
    "middle_name": "Астромерович",
    "last_name": "Звяегольцев",
    "last_name_2": "Звягольцев",
    # "birthday": "03.05.1993",
    "phone": "+7 (933) 575-35-35",
    "email": "aristaniy93@gmail.com",
    "telegram": "https://t.me/aristaniy93",
    "whatsapp": "https://wa.me/aristaniy93",
    "other_site": "https://www.aristaniy93.ru",
    "habr_career": "https://career.habr.ru/aristaniy93",
    "linkedin": "https://linkedin.com/in/aristaniy-zvyagoltsev-f3e57c712",
    "github": "https://github.com/aristaniy93",
    "telegram_2": "@aristaniy93",
    "telegram_3": "aristaniy93",
}

# Личные данные-пустышки для анонимизации (женский пол)
DUMMY_PERSONAL_INFO_FEMALE = {
    "first_name": "Аристания",
    "first_name_2": "Ари́стания",
    "first_name_3": "Ариста́ния",
    "middle_name": "Астромеровна",
    "last_name": "Звяегольцева",
    "last_name_2": "Звягольцева",
    # "birthday": "03.05.1993",
    "phone": "+7 (933) 575-35-35",
    "email": "aristaniya93@gmail.com",
    "telegram": "https://t.me/aristaniya93",
    "whatsapp": "https://wa.me/aristaniya93",
    "other_site": "https://www.aristaniya93.ru",
    "habr_career": "https://career.habr.ru/aristaniya93",
    "linkedin": "https://linkedin.com/in/aristaniya-zvyagoltseva-f3e57c712",
    "github": "https://github.com/aristaniya93",
    "telegram_2": "@aristaniya93",
    "telegram_3": "aristaniya93",
}

# Пути к файлам логов и настроек
SECRETS_FILE = "data_folder/secrets/secrets.yaml"
APP_CONFIG_FILE = "data_folder/app_config/app_config.yaml"
SEARCH_CONFIG_FILE = "data_folder/search_config/search_config.yaml"
SEARCH_CONFIG_FILE_TMP = "data_folder/output/search_config_tmp.yaml"
LAST_RUN_FILE = "data_folder/output/last_run.yaml"
LOGS_DIR = "logs"
DEBUG_DIR = "data_folder/debug"
BROWSER_STORAGE_STATE = "data_folder/browser_session/hh_state.json"

# Словарь для подсчета стоимости запроса к модели
# Per-model token pricing (input/output cost per token in USD)
PRICE_DICT: dict[str, dict[str, float]] = {
    # Gemini
    "gemini-3.1-flash-lite-preview": {
        "input_cost_per_token": 0.075 / 1_000_000,
        "output_cost_per_token": 0.30 / 1_000_000,
    },
    "gemini-3-flash-preview": {
        "input_cost_per_token": 0.15 / 1_000_000,
        "output_cost_per_token": 0.60 / 1_000_000,
    },
    # OpenAI
    "gpt-4o-mini": {
        "input_cost_per_token": 0.15 / 1_000_000,
        "output_cost_per_token": 0.60 / 1_000_000,
    },
    "gpt-4o": {
        "input_cost_per_token": 2.50 / 1_000_000,
        "output_cost_per_token": 10.00 / 1_000_000,
    },
    "gpt-5-mini": {
        "input_cost_per_token": 0.15 / 1_000_000,
        "output_cost_per_token": 0.60 / 1_000_000,
    },
    "gpt-5-nano": {
        "input_cost_per_token": 0.10 / 1_000_000,
        "output_cost_per_token": 0.40 / 1_000_000,
    },
    # Anthropic
    "anthropic/claude-haiku-4-5": {
        "input_cost_per_token": 0.80 / 1_000_000,
        "output_cost_per_token": 4.00 / 1_000_000,
    },
    "anthropic/claude-sonnet-4": {
        "input_cost_per_token": 3.00 / 1_000_000,
        "output_cost_per_token": 15.00 / 1_000_000,
    },
    "anthropic/claude-sonnet-4-5": {
        "input_cost_per_token": 3.00 / 1_000_000,
        "output_cost_per_token": 15.00 / 1_000_000,
    },
    "anthropic/claude-sonnet-4-6": {
        "input_cost_per_token": 3.00 / 1_000_000,
        "output_cost_per_token": 15.00 / 1_000_000,
    },
    # DeepSeek
    "deepseek/deepseek-chat-v3.1": {
        "input_cost_per_token": 0.15 / 1_000_000,
        "output_cost_per_token": 0.75 / 1_000_000,
    },
    "deepseek/deepseek-chat-v3.2": {
        "input_cost_per_token": 0.26 / 1_000_000,
        "output_cost_per_token": 0.38 / 1_000_000,
    },
    "deepseek/deepseek-v4-flash": {
        "input_cost_per_token": 0.14 / 1_000_000,
        "output_cost_per_token": 0.28 / 1_000_000,
    },
    # Qwen
    "qwen/qwen3.5-flash-02-23": {
        "input_cost_per_token": 0.065 / 1_000_000,
        "output_cost_per_token": 0.26 / 1_000_000,
    },
    "qwen/qwen3.6-plus": {
        "input_cost_per_token": 0.325 / 1_000_000,
        "output_cost_per_token": 1.30 / 1_000_000,
    },
    # NVIDIA NIM
    "meta/llama-3.3-70b-instruct": {
        "input_cost_per_token": 0.27 / 1_000_000,
        "output_cost_per_token": 0.85 / 1_000_000,
    },
    "meta/llama-3.1-405b-instruct": {
        "input_cost_per_token": 1.00 / 1_000_000,
        "output_cost_per_token": 3.00 / 1_000_000,
    },
    "nvidia/llama-3.1-nemotron-70b-instruct": {
        "input_cost_per_token": 0.27 / 1_000_000,
        "output_cost_per_token": 0.85 / 1_000_000,
    },
    # Groq
    "llama-3.3-70b-versatile": {
        "input_cost_per_token": 0.59 / 1_000_000,
        "output_cost_per_token": 0.79 / 1_000_000,
    },
    "llama-3.1-8b-instant": {
        "input_cost_per_token": 0.05 / 1_000_000,
        "output_cost_per_token": 0.08 / 1_000_000,
    },
    "deepseek-r1-distill-llama-70b": {
        "input_cost_per_token": 0.75 / 1_000_000,
        "output_cost_per_token": 0.99 / 1_000_000,
    },
    # Cerebras
    "llama-3.3-70b": {
        "input_cost_per_token": 0.85 / 1_000_000,
        "output_cost_per_token": 1.20 / 1_000_000,
    },
    "llama-3.1-8b": {
        "input_cost_per_token": 0.10 / 1_000_000,
        "output_cost_per_token": 0.10 / 1_000_000,
    },
    "qwen-3-32b": {
        "input_cost_per_token": 0.45 / 1_000_000,
        "output_cost_per_token": 0.65 / 1_000_000,
    },
}
