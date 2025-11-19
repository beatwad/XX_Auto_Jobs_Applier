# Личные данные-пустышки для анонимизации (мужской пол)
DUMMY_PERSONAL_INFO_MALE = {
    "first_name": "Аристаний",
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
    "skype": "aristaniy93",
    "linkedin": "https://linkedin.com/in/aristaniy-zvyagoltsev-f3e57c712",
    "github": "https://github.com/aristaniy93",
    "moi_krug": "https://moi-krug.ru/aristaniy93",
    "livejournal": "https://aristaniy93.livejournal.com",
}

# Личные данные-пустышки для анонимизации (женский пол)
DUMMY_PERSONAL_INFO_FEMALE = {
    "first_name": "Аристания",
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
    "skype": "aristaniya93",
    "linkedin": "https://linkedin.com/in/aristaniya-zvyagoltseva-f3e57c712",
    "github": "https://github.com/aristaniya93",
    "moi_krug": "https://moi-krug.ru/aristaniya93",
    "livejournal": "https://aristaniya93.livejournal.com",
}

# Пути к файлам логов и настроек
SECRETS_FILE = "data_folder/secrets/secrets.yaml"
SEARCH_CONFIG_FILE = "data_folder/search_config/search_config.yaml"
SEARCH_CONFIG_FILE_TMP = "data_folder/output/search_config_tmp.yaml"
LAST_RUN_FILE = "data_folder/output/last_run.yaml"
LOGS_DIR = "logs"

# Словарь для подсчета стоимости запроса к модели
PRICE_DICT = {
    "gpt-4o": {
        "price_per_input_token": 2.5e-6,
        "price_per_output_token": 1e-5,
    },
    "gpt-4o-mini": {
        "price_per_input_token": 1.5e-7,
        "price_per_output_token": 6e-7,
    },
    "gemini-2.0-flash": {
        "price_per_input_token": 1e-7,
        "price_per_output_token": 4e-7,
    },
    "GigaChat": {  # цены рассчитаны из учета курс 100 руб за $
        "price_per_input_token": 2e-6,
        "price_per_output_token": 2e-6,
    },
    "GigaChat-Pro": {
        "price_per_input_token": 1.5e-5,
        "price_per_output_token": 1.5e-5,
    },
    "GigaChat-Max": {
        "price_per_input_token": 1.95e-5,
        "price_per_output_token": 1.95e-5,
    },
}
