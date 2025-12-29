import yaml  # Required for loading YAML if the functions were to take file paths.

# For this solution, we assume data is already parsed.


def _format_value(value):
    """
    Formats a value for display.
    Returns None if the value is considered empty (None, empty string, empty list/dict).
    Converts booleans to 'Да'/'Нет'.
    Joins list items into a comma-separated string, returning None if list is empty or contains only empty items.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, str):
        return value.strip() if value.strip() else None
    if isinstance(value, list):
        # Filter out empty strings or None from list before joining
        filtered_list = [
            str(item) for item in value if item is not None and str(item).strip() != ""
        ]
        return ", ".join(filtered_list) if filtered_list else None
    if isinstance(value, dict):
        return value if value else None  # Return dict if not empty, else None (for specific checks)
    return str(value)  # For numbers, etc.


def _indent_text(text, prefix="  "):
    """Indents a block of text. Returns empty string if text is None or empty/whitespace."""
    formatted_text = _format_value(text)
    if not formatted_text:
        return ""
    return "\n".join(prefix + line for line in formatted_text.splitlines())


def transform_resume_data(data: dict) -> str:
    """
    Transforms resume YAML data into a human-readable string.
    Fields/sections are omitted if their data is missing or empty.
    Supports the Resume structure from src/views/resume.py.
    """
    if not isinstance(data, dict) or not data:
        return "Нет данных для отображения в резюме."

    title = "Резюме"
    content_lines = []

    # Personal Information
    pi = data.get("personal_information", {})
    if isinstance(pi, dict) and pi:
        pi_section_lines = []

        name_parts = []
        fn = _format_value(pi.get("first_name"))
        if fn:
            name_parts.append(fn)
        mn = _format_value(pi.get("middle_name"))
        if mn:
            name_parts.append(mn)
        ln = _format_value(pi.get("last_name"))
        if ln:
            name_parts.append(ln)
        if name_parts:
            pi_section_lines.append(f"  ФИО: {' '.join(name_parts)}")

        for key, label in [
            ("email", "Email"),
            ("phone", "Телефон"),
            ("telegram", "Telegram"),
            ("whatsapp", "WhatsApp"),
            ("linkedin", "LinkedIn"),
            ("habr_career", "Хабр Карьера"),
            ("sex", "Пол"),
            ("citizenship", "Гражданство"),
            ("legal_authorization", "Разрешение на работу"),
        ]:
            val = _format_value(pi.get(key))
            if val is not None:
                pi_section_lines.append(f"  {label}: {val}")

        has_vehicle = pi.get("has_vehicle")  # Boolean
        formatted_has_vehicle = _format_value(has_vehicle)
        if formatted_has_vehicle is not None:
            pi_section_lines.append(f"  Наличие автомобиля: {formatted_has_vehicle}")

        if pi_section_lines:
            content_lines.append("\nЛИЧНАЯ ИНФОРМАЦИЯ:")
            content_lines.extend(pi_section_lines)

    # Top-level fields (Area, Driving License, Citizenship fallback, Legal Auth fallback)
    # Note: citizenship and legal_authorization might be in personal_information (nested) OR top-level
    # depending on how exactly pydantic parses it or how scraper puts it.
    # The new model puts them in PersonalInformation, but scraper might put them in top-level too as legacy.
    # We check top-level if not found in PI or just add them if present and different.

    # Actually, looking at the Pydantic model:
    # citizenship and legal_authorization are fields in BOTH Resume (top-level) and PersonalInformation.
    # We should probably display top-level ones if PI ones are missing, or just check both.

    tl_lines = []
    area = _format_value(data.get("area"))
    if area:
        tl_lines.append(f"  Регион: {area}")

    driving_license = _format_value(data.get("driving_license"))
    if driving_license:
        tl_lines.append(f"  Водительские права: {driving_license}")

    # Check top-level citizenship/auth if not already printed from PI
    if not _format_value(pi.get("citizenship")):
        citizenship = _format_value(data.get("citizenship"))
        if citizenship:
            tl_lines.append(f"  Гражданство: {citizenship}")

    if not _format_value(pi.get("legal_authorization")):
        legal_auth = _format_value(data.get("legal_authorization"))
        if legal_auth:
            tl_lines.append(f"  Разрешение на работу: {legal_auth}")

    if tl_lines:
        # If we didn't start PI section yet, add header
        if "\nЛИЧНАЯ ИНФОРМАЦИЯ:" not in content_lines:
            content_lines.append("\nЛИЧНАЯ ИНФОРМАЦИЯ (прочее):")
        content_lines.extend(tl_lines)

    # Job Preferences
    jp = data.get("job_preferences", {})
    if isinstance(jp, dict) and jp:
        jp_lines = []
        for key, label in [
            ("job_type", "Тип занятости"),
            ("job_format", "Формат работы"),
            ("salary", "Зарплата"),
            ("time_to_travel", "Время в пути"),
            ("readiness_to_job_trips", "Готовность к командировкам"),
        ]:
            val = _format_value(jp.get(key))
            if val:
                jp_lines.append(f"  {label}: {val}")

        if jp_lines:
            content_lines.append("\nПРЕДПОЧТЕНИЯ ПО РАБОТЕ:")
            content_lines.extend(jp_lines)

    # About Me
    about_me = _indent_text(data.get("about_me"), "  ")
    if about_me:
        content_lines.append("\nОБО МНЕ:")
        content_lines.append(about_me)

    # Skills
    skills = _format_value(data.get("skills"))
    if skills:
        content_lines.append("\nНАВЫКИ:")
        content_lines.append(f"  {skills}")

    # Experience (Text blob)
    total_exp = _format_value(data.get("total_experience"))
    experience = _indent_text(data.get("experience"), "  ")

    if total_exp or experience:
        content_lines.append("\nОПЫТ РАБОТЫ:")
        if total_exp:
            content_lines.append(f"  Общий опыт: {total_exp}")
        if experience:
            content_lines.append(experience)

    # Education (Text blob)
    educations = _indent_text(data.get("educations"), "  ")
    if educations:
        content_lines.append("\nОБРАЗОВАНИЕ:")
        content_lines.append(educations)

    # Additional Education (Text blob)
    add_edu = _indent_text(data.get("additional_education"), "  ")
    if add_edu:
        content_lines.append("\nДОПОЛНИТЕЛЬНОЕ ОБРАЗОВАНИЕ:")
        content_lines.append(add_edu)

    # Exams (Text blob)
    exams = _indent_text(data.get("exams"), "  ")
    if exams:
        content_lines.append("\nЭКЗАМЕНЫ / ТЕСТЫ:")
        content_lines.append(exams)

    # Certificates (Text blob)
    certificates = _indent_text(data.get("certificates"), "  ")
    if certificates:
        content_lines.append("\nСЕРТИФИКАТЫ:")
        content_lines.append(certificates)

    # Recommendations (Text blob)
    recommendations = _indent_text(data.get("recommendations"), "  ")
    if recommendations:
        content_lines.append("\nРЕКОМЕНДАЦИИ:")
        content_lines.append(recommendations)

    if not content_lines:
        return f"Нет данных для отображения в {title.lower()}."

    final_output = [title, "=" * 3]
    final_output.extend(content_lines)
    return "\n".join(final_output)


def transform_vacancy_data(data: dict) -> str:
    """
    Transforms vacancy YAML data into a human-readable string.
    Fields/sections are omitted if their data is missing or empty.
    Supports the Job structure from src/views/job.py.
    """
    if not isinstance(data, dict) or not data:
        return "Нет данных для отображения вакансии."

    title = "Информация о вакансии"
    content_lines = []

    # Basic Info
    main_info_lines = []
    for key, label in [
        ("job_title", "Название вакансии"),
        ("company_name", "Компания"),
        ("vacancy_id", "ID вакансии"),
    ]:
        val = _format_value(data.get(key))
        if val:
            main_info_lines.append(f"{label}: {val}")

    if main_info_lines:
        content_lines.extend(main_info_lines)

    # Salary
    salary = _format_value(data.get("salary"))
    if salary:
        content_lines.append("\nЗАРПЛАТА:")
        content_lines.append(f"  {salary}")

    # Work Conditions
    wc_lines = []
    for key, label in [
        ("experience", "Требуемый опыт"),
        ("employment", "Тип занятости"),
        ("schedule", "График работы"),
        ("working_hours", "Рабочие часы"),
        ("work_formats", "Формат работы"),
        ("hiring_formats", "Формат оформления"),
    ]:
        val = _format_value(data.get(key))
        if val:
            wc_lines.append(f"  {label}: {val}")

    if wc_lines:
        content_lines.append("\nУСЛОВИЯ РАБОТЫ:")
        content_lines.extend(wc_lines)

    # Description
    description = _indent_text(data.get("description"), "  ")
    if description:
        content_lines.append("\nОПИСАНИЕ ВАКАНСИИ:")
        content_lines.append(description)

    # Skills
    skills = _format_value(data.get("skills"))
    if skills:
        content_lines.append("\nНАВЫКИ:")
        content_lines.append(f"  {skills}")

    if not content_lines:
        return f"Нет данных для отображения в {title.lower()}."

    final_output = [title, "=" * 3]
    final_output.extend(content_lines)
    return "\n".join(final_output)


# Helpers for search_config
def _get_selected_option(group_data, option_map):
    if not isinstance(group_data, dict):
        return None
    for key, value in group_data.items():
        if value is True:
            return option_map.get(key, key)
    return None


def _get_multiple_selected_options(group_data, option_map):
    if not isinstance(group_data, dict):
        return None
    selected = [option_map.get(k, k) for k, v in group_data.items() if v is True]
    return ", ".join(selected) if selected else None


def transform_search_config_data(data: dict) -> str:
    """
    Transforms search configuration YAML data into a human-readable string.
    Fields/sections are omitted if their data is missing or empty.
    """
    if not isinstance(data, dict) or not data:
        return "Нет данных для отображения конфигурации поиска."

    title = "Параметры Поиска Вакансий"
    content_lines = []

    # --- Основное ---
    sc_main_lines = []
    for key, label in [
        ("job_title", "Должность для поиска"),
        ("keywords", "Ключевые слова"),
        ("words_to_exclude", "Исключить слова"),
        ("professional_role", "Специализация"),
        ("industry", "Отрасль компании"),
        ("area", "Регионы"),
    ]:
        val = _format_value(data.get(key))
        if val:
            sc_main_lines.append(f"  {label}: {val}")

    districts = _format_value(data.get("districts"))
    if districts:
        sc_main_lines.append(f"  Районы: {districts}")

    if sc_main_lines:
        content_lines.append("\nОСНОВНЫЕ ПАРАМЕТРЫ ПОИСКА:")
        content_lines.extend(sc_main_lines)

    # --- Финансовые условия ---
    sc_financial_lines = []
    salary_val = _format_value(data.get("salary"))
    if salary_val:
        sc_financial_lines.append(f"  Уровень дохода от: {salary_val}")

    only_with_salary = data.get("only_with_salary")  # boolean
    if only_with_salary is not None:
        sc_financial_lines.append(
            f"  Показывать только с указанной з/п: {_format_value(only_with_salary)}"
        )

    currency_map = {"RUR": "Рубли (RUR)", "EUR": "Евро (EUR)", "USD": "Доллары (USD)"}
    selected_currency = _get_selected_option(data.get("currency", {}), currency_map)
    if selected_currency:
        sc_financial_lines.append(f"  Валюта: {selected_currency}")

    if sc_financial_lines:
        content_lines.append("\nФИНАНСОВЫЕ УСЛОВИЯ:")
        content_lines.extend(sc_financial_lines)

    # --- Образование и Опыт ---
    sc_edu_exp_lines = []
    education_map = {
        "not_needed": "Не требуется или не указано",
        "middle": "Среднее профессиональное",
        "higher": "Высшее",
    }
    selected_education = _get_selected_option(data.get("education", {}), education_map)
    if selected_education:
        sc_edu_exp_lines.append(f"  Образование: {selected_education} (не участвует в поиске)")

    experience_map = {
        "doesntMatter": "Не имеет значения",
        "noExperience": "Нет опыта",
        "between1And3": "От 1 года до 3 лет",
        "between3And6": "От 3 до 6 лет",
        "moreThan6": "Более 6 лет",
    }
    selected_experience = _get_multiple_selected_options(data.get("experience", {}), experience_map)
    if selected_experience:
        sc_edu_exp_lines.append(f"  Требуемый опыт: {selected_experience}")

    if sc_edu_exp_lines:
        content_lines.append("\nОБРАЗОВАНИЕ И ОПЫТ:")
        content_lines.extend(sc_edu_exp_lines)

    # --- Условия работы ---
    sc_work_cond_lines = []
    employment_map = {
        "FULL": "Полная занятость",
        "PART": "Частичная занятость",
        "PROJECT": "Проектная работа/разовое задание",
        "FLY_IN_FLY_OUT": "Вахта",
        "INTERNSHIP": "Стажировка",
        "ACCEPT_TEMPORARY": "Оформление по ГПХ",
    }
    selected_employment = _get_multiple_selected_options(data.get("employment", {}), employment_map)
    if selected_employment:
        sc_work_cond_lines.append(f"  Тип занятости: {selected_employment}")

    job_format_map = {
        "ON_SITE": "На месте работодателя",
        "REMOTE": "Удаленно",
        "HYBRID": "Гибрид",
        "FIELD_WORK": "Разъездной",
    }
    selected_job_format = _get_multiple_selected_options(data.get("job_format", {}), job_format_map)
    if selected_job_format:
        sc_work_cond_lines.append(f"  Формат работы: {selected_job_format}")

    if sc_work_cond_lines:
        content_lines.append("\nУСЛОВИЯ РАБОТЫ:")
        content_lines.extend(sc_work_cond_lines)

    # --- Прочие параметры вакансии ---
    vacancy_label_map = {
        "with_address": "С адресом",
        "accept_handicapped": "Доступные людям с инвалидностью",
        "not_from_agency": "Без вакансий от кадровых агентств",
        "accept_kids": "Доступные с 14 лет",
        "accredited_it": "От аккредитованных ИТ-компаний",
        "low_performance": "Меньше 10 откликов",
    }
    selected_labels = _get_multiple_selected_options(
        data.get("vacancy_label", {}), vacancy_label_map
    )
    if selected_labels:
        content_lines.append("\nДРУГИЕ ПАРАМЕТРЫ ВАКАНСИИ:")
        content_lines.append(f"  {selected_labels}")

    # --- Списки и Шаблоны ---
    sc_lists_tpl_lines = []
    blacklist = _format_value(data.get("job_blacklist"))
    if blacklist:
        sc_lists_tpl_lines.append(f"  Черный список компаний: {blacklist}")

    if sc_lists_tpl_lines:
        content_lines.append("\nСПИСКИ ИСКЛЮЧЕНИЙ И ШАБЛОНЫ:")
        content_lines.extend(sc_lists_tpl_lines)

    if not content_lines:
        return f"Нет данных для отображения в {title.lower()}."

    final_output = [title, "=" * 3]
    final_output.extend(content_lines)
    return "\n".join(final_output)


if __name__ == "__main__":
    # Test Data for New Resume Structure
    resume_data_new = {
        "personal_information": {
            "first_name": "Аристаний",
            "middle_name": "Астромерович",
            "last_name": "Звяегольцев",
            "email": "aristaniy93@gmail.com",
            "phone": "+7 (933) 575-35-35",
            "telegram": "@Tatyan_kts",
            "sex": "Мужской",
            "citizenship": "Россия",
        },
        "area": "Орел",
        "job_preferences": {
            "salary": "300000 RUR",
            "job_format": "Удаленно",
            "job_type": "Полная занятость",
        },
        "skills": "Python, SQL, Django, FastAPI",
        "total_experience": "4 года",
        "experience": "ООО Green-Park: Разработчик Python...\nПРАЙМ ГРУП: Разработчик...",
        "educations": "МГУ, ВМК, 2019",
        "about_me": "Специализируюсь на Python...",
    }

    vacancy_data_new = {
        "job_title": "Junior Full Stack",
        "company_name": "Max Solutions",
        "salary": "300000 - 400000 KZT",
        "experience": "Нет опыта",
        "employment": "Полная",
        "description": "Ищем разработчика...",
        "skills": "Python, FastAPI, React",
    }

    search_config_yaml_content = """
job_title: Программист Python
text:  Аналитик, программист
search_field:
  name: false
  company_name: true
  description: true
words_to_exclude: Google, Meta
professional_role: Программист
industry: Банк, Финансовые услуги
area:  Москва, Санкт-Петербург
districts: Северное Бутово, Замоскворечье, Чертаново
salary: 300000
only_with_salary: False
currency:
  RUR: true
  EUR: false
  USD: false
education:
  not_needed: true
  middle: false
  higher: false
experience:
  doesntMatter: false
  noExperience: true
  between1And3: true
  between3And6: false
  moreThan6: false
employment:
  FULL: true
  PART: true
  PROJECT: false
  FLY_IN_FLY_OUT: false
  ACCEPT_TEMPORARY: false
schedule:
  ON_SITE: true
  REMOTE: true
  HYBRID: false
  FIELD_WORK: false
label:
  with_address: true
  accept_handicapped: false
  not_from_agency: false
  accept_kids: false
  accredited_it: true
  low_performance: false
order_by:
  relevance: true
  publication_time: false
  salary_desc: false
  salary_asc: false
period:
  all_time: false
  month: true
  week: false
  three_days: false
  one_day: false
job_blacklist: Google, Meta
cover_letter: |
  Здравствуйте! Прошу рассмотреть моё резюме на роль разработчика Python в вашу компанию.

  Кратко о себе:
  - опыт работы: 4 года
  - ожидания по зарплате: от 200000 до 400000 руб
  - основной стек: Python, SQL, Django, React, REST API, Redis
  - есть опыт работы с Docker/Docker Compose
  - знаком с Airflow, FastAPI, Flask
  - проекты веду в git

  тг для связи: greg95
apply_once_at_company: true
skip_companies_with_test: false
access_token: agqt34jaegag35623
refresh_token: lgjaglj436l5j26h2
max_applies_num: 100
tariff: 14days
"""
    search_config_data = yaml.safe_load(search_config_yaml_content)

    print("--- Human-Readable Resume (New Structure) ---")
    print(transform_resume_data(resume_data_new))
    print("\n\n--- Human-Readable Vacancy (New Structure) ---")
    print(transform_vacancy_data(vacancy_data_new))
    print("\n\n--- Human-Readable Search Config (Full) ---")
    print(transform_search_config_data(search_config_data))
