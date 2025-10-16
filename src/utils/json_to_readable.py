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
    """
    if not isinstance(data, dict) or not data:
        return "Нет данных для отображения в резюме."

    title = "Резюме"
    content_lines = []

    # Personal Information
    pi = data.get("personal_information", {})
    if isinstance(pi, dict) and pi:  # Ensure pi is a non-empty dict
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
            ("current_city", "Текущий город"),
            ("sex", "Пол"),
            ("age", "Возраст"),
            # ("birthday", "Дата рождения"),
            ("linkedin", "LinkedIn"),
            ("livejournal", "LiveJournal"),
            ("moi_krug", "Мой Круг"),
            ("other_site", "Другой сайт"),
            ("preferred_contact", "Предпочтительный способ связи"),
        ]:
            val = _format_value(pi.get(key))
            if val is not None:
                pi_section_lines.append(f"  {label}: {val}")

        citizenship = _format_value(pi.get("citizenship"))
        if citizenship:
            pi_section_lines.append(f"  Гражданство: {citizenship}")

        legal_auth = _format_value(pi.get("legal_authorization"))
        if legal_auth:
            pi_section_lines.append(f"  Разрешение на работу: {legal_auth}")

        has_vehicle = pi.get("has_vehicle")  # Boolean, _format_value handles it
        formatted_has_vehicle = _format_value(has_vehicle)
        if formatted_has_vehicle is not None:
            pi_section_lines.append(f"  Наличие автомобиля: {formatted_has_vehicle}")

        if pi_section_lines:
            content_lines.append("\nЛИЧНАЯ ИНФОРМАЦИЯ:")
            content_lines.extend(pi_section_lines)

    # About Me
    about_me_text = _indent_text(data.get("about_me"), "  ")
    if about_me_text:
        content_lines.append("\nОБО МНЕ:")
        content_lines.append(about_me_text)

    # Skills
    skills_list = _format_value(data.get("skills", []))
    if skills_list:
        content_lines.append("\nНАВЫКИ:")
        content_lines.append(f"  {skills_list}")

    # Salary Expectations
    se = data.get("salary_expectations", {})
    if isinstance(se, dict):
        amount = _format_value(se.get("amount"))
        currency = _format_value(se.get("currency"))
        if amount and currency:
            content_lines.append("\nЗАРПЛАТНЫЕ ОЖИДАНИЯ:")
            content_lines.append(f"  {amount} {currency}")

    # Experience Details
    exp_data = data.get("experience_details", {})
    if isinstance(exp_data, dict):
        exp_section_lines = []
        total_years = _format_value(exp_data.get("total_experience_years"))
        if total_years:
            exp_section_lines.append(f"  Общий опыт: {total_years} лет")

        jobs = exp_data.get("details", [])
        if isinstance(jobs, list):
            for job in jobs:
                if not isinstance(job, dict):
                    continue
                job_lines = []
                company = _format_value(job.get("company"))
                if company:
                    job_lines.append(f"  Компания: {company}")

                position = _format_value(job.get("position"))
                if position:
                    job_lines.append(f"    Должность: {position}")

                start_date = _format_value(job.get("start_date"))
                end_date = _format_value(job.get("end_date"))
                period_parts = []
                if start_date:
                    period_parts.append(start_date)
                if end_date:
                    period_parts.append(end_date)
                else:
                    period_parts.append(
                        "настоящее время"
                    )  # Default if start is present but end is not

                if start_date:  # Only show period if at least start_date is present
                    job_lines.append(f"    Период: {' - '.join(period_parts)}")

                description = _indent_text(job.get("description"), "      ")
                if description:
                    job_lines.append("    Обязанности и достижения:")
                    job_lines.append(description)

                industries = _format_value(job.get("industries", []))
                if industries:
                    job_lines.append(f"    Отрасли: {industries}")

                if job_lines:  # Add job entry if it has any content
                    exp_section_lines.extend(
                        job_lines
                    )  # Consider adding a separator or ensuring company starts without indent if it's the first line for a job.
                    # Current structure: company will be indented if total_years is present.

        if exp_section_lines:
            content_lines.append("\nОПЫТ РАБОТЫ:")
            # Refined logic for job entries for better formatting
            # If total_years is present, it's already added to exp_section_lines
            # The job_lines are added individually. We need to ensure proper structure.

            # Revised Experience Output:
            current_exp_content = []
            if total_years:
                current_exp_content.append(f"  Общий опыт: {total_years} лет")

            job_details_output = []
            if isinstance(jobs, list):
                for job_idx, job in enumerate(jobs):
                    if not isinstance(job, dict):
                        continue

                    single_job_lines = []
                    company = _format_value(job.get("company"))
                    position = _format_value(job.get("position"))

                    # Combine company and position if both exist for a cleaner header
                    job_header_parts = []
                    if company:
                        job_header_parts.append(company)
                    if position:
                        job_header_parts.append(f"({position})")

                    if job_header_parts:
                        single_job_lines.append(
                            f"  {'- ' if job_idx > 0 or total_years else ''}{' '.join(job_header_parts)}"
                        )

                    start_date = _format_value(job.get("start_date"))
                    end_date = _format_value(job.get("end_date"))
                    period_str = None
                    if start_date:
                        period_parts = [start_date]
                        period_parts.append(end_date if end_date else "настоящее время")
                        period_str = " - ".join(period_parts)

                    if period_str:
                        single_job_lines.append(f"    Период: {period_str}")

                    description = _indent_text(
                        job.get("description"), "    "
                    )  # Indent relative to job header
                    if description:
                        single_job_lines.append("    Обязанности и достижения:")
                        single_job_lines.append(description)

                    industries = _format_value(job.get("industries", []))
                    if industries:
                        single_job_lines.append(f"    Отрасли: {industries}")

                    if single_job_lines:
                        job_details_output.extend(single_job_lines)

            if job_details_output:
                current_exp_content.extend(job_details_output)

            if current_exp_content:
                # Check if we already added to content_lines for exp, if not:
                if not any("ОПЫТ РАБОТЫ:" in line for line in content_lines):
                    content_lines.append("\nОПЫТ РАБОТЫ:")
                content_lines.extend(current_exp_content)

    # Education Details
    edu = data.get("education_details", {})
    if isinstance(edu, dict) and edu:
        edu_section_lines = []
        level = _format_value(edu.get("level"))
        if level:
            edu_section_lines.append(f"  Уровень: {level}")

        edu_types = {
            "primary": "Основное высшее",
            "elementary": "Базовое/Среднее",
            "additional": "Дополнительное",
            "attestation": "Аттестация",
        }
        for edu_key, edu_title_label in edu_types.items():
            edu_list = edu.get(edu_key, [])
            if isinstance(edu_list, list) and edu_list:
                current_edu_type_lines = []
                for item in edu_list:
                    if not isinstance(item, dict):
                        continue
                    item_lines = []
                    name = _format_value(item.get("name"))
                    if name:
                        item_lines.append(f"      Учебное заведение: {name}")

                    organization = _format_value(item.get("organization"))
                    if organization:
                        item_lines.append(f"        Организация: {organization}")

                    result = _format_value(item.get("result"))
                    if result:
                        item_lines.append(f"        Результат/Специальность: {result}")

                    year = _format_value(item.get("year"))
                    if year:
                        item_lines.append(f"        Год окончания: {year}")

                    if item_lines:
                        current_edu_type_lines.extend(item_lines)

                if current_edu_type_lines:
                    edu_section_lines.append(
                        f"\n    {edu_title_label}:"
                    )  # Add a bit more indent for clarity
                    edu_section_lines.extend(current_edu_type_lines)

        if edu_section_lines:
            content_lines.append("\nОБРАЗОВАНИЕ:")
            content_lines.extend(edu_section_lines)

    # Certifications
    certs = data.get("certifications", [])
    if isinstance(certs, list) and certs:
        cert_section_lines = []
        for cert in certs:
            if not isinstance(cert, dict):
                continue
            title = _format_value(cert.get("title"))
            if title:
                cert_section_lines.append(f"  - {title}")
                achieved_at = _format_value(cert.get("achieved_at"))
                if achieved_at:
                    cert_section_lines.append(f"    Получен: {achieved_at}")
        if cert_section_lines:
            content_lines.append("\nСЕРТИФИКАТЫ:")
            content_lines.extend(cert_section_lines)

    # Languages
    langs = data.get("languages", {})
    if isinstance(langs, dict) and langs:
        lang_section_lines = []
        for lang, level in langs.items():
            formatted_lang = _format_value(lang)
            formatted_level = _format_value(level)
            if formatted_lang and formatted_level:
                lang_section_lines.append(f"  - {formatted_lang}: {formatted_level}")
        if lang_section_lines:
            content_lines.append("\nЗНАНИЕ ЯЗЫКОВ:")
            content_lines.extend(lang_section_lines)

    # Work Preferences
    main_title = ""
    wp = data.get("work_preferences", {})
    if isinstance(wp, dict) and wp:
        wp_section_lines = []
        for key, label in [
            ("position", "Желаемая должность"),
            ("can_relocate", "Готовность к переезду"),
            ("ready_to_business_trips", "Готовность к командировкам"),
            ("travel_time_to_work", "Время в пути до работы"),
        ]:
            val = _format_value(wp.get(key))
            if val is not None:
                if key == "position":
                    main_title = val
                wp_section_lines.append(f"  {label}: {val}")

        for key, label in [
            ("employments", "Типы занятости"),
            ("schedules", "Графики работы"),
            ("professional_roles", "Профессиональные роли"),
        ]:
            val_list = _format_value(wp.get(key, []))
            if val_list:
                wp_section_lines.append(f"  {label}: {val_list}")

        if wp_section_lines:
            content_lines.append("\nПРЕДПОЧТЕНИЯ ПО РАБОТЕ:")
            content_lines.extend(wp_section_lines)

    # Availability
    avail = data.get("availability", {})
    if isinstance(avail, dict):
        notice = _format_value(avail.get("notice_period"))
        if notice:
            content_lines.append("\nДОСТУПНОСТЬ:")
            content_lines.append(f"  Срок уведомления об увольнении: {notice}")

    # Recommendations
    recs = data.get("recommendation", [])
    if isinstance(recs, list) and recs:
        rec_section_lines = []
        for rec in recs:
            if not isinstance(rec, dict):
                continue
            name = _format_value(rec.get("name"))
            if name:
                rec_section_lines.append(f"  - {name}")
                for key, label in [
                    ("organization", "Организация"),
                    ("position", "Должность"),
                    ("contact", "Контакт"),
                ]:
                    val = _format_value(rec.get(key))
                    if val:
                        rec_section_lines.append(f"    {label}: {val}")
        if rec_section_lines:
            content_lines.append("\nРЕКОМЕНДАЦИИ:")
            content_lines.extend(rec_section_lines)

    if not content_lines:
        return f"Нет данных для отображения в {title.lower()}."

    final_output = [main_title, "=" * 3]
    final_output.extend(content_lines)
    return "\n".join(final_output)


def transform_vacancy_data(data: dict) -> str:
    """
    Transforms vacancy YAML data into a human-readable string.
    Fields/sections are omitted if their data is missing or empty.
    """
    if not isinstance(data, dict) or not data:
        return "Нет данных для отображения вакансии."

    title = "Информация о вакансии"
    content_lines = []

    main_info_lines = []
    for key, label in [
        ("job_title", "Название вакансии"),
        ("company_name", "Компания"),
        ("area", "Город/Регион"),
    ]:
        val = _format_value(data.get(key))
        if val:
            main_info_lines.append(f"{label}: {val}")  # No indent for top-level info
    if main_info_lines:
        content_lines.extend(main_info_lines)

    # Salary
    salary = data.get("salary", {})
    if isinstance(salary, dict) and salary:
        salary_lines = []
        s_from = _format_value(salary.get("from"))
        s_to = _format_value(salary.get("to"))
        s_currency = _format_value(salary.get("currency"))
        s_gross_val = salary.get("gross")  # Keep boolean
        s_gross_text = ""
        if isinstance(s_gross_val, bool):  # Only add gross text if key exists
            s_gross_text = " (до вычета налогов)" if s_gross_val else " (на руки)"

        salary_parts = []
        if s_from:
            salary_parts.append(f"От {s_from}")
        if s_to:
            salary_parts.append(f"До {s_to}")
        if s_currency:
            salary_parts.append(s_currency)

        if salary_parts:
            salary_lines.append(f"  {' '.join(salary_parts)}{s_gross_text}")
        elif s_currency and s_gross_text:  # e.g. only currency and gross status specified
            salary_lines.append(f"  Валюта: {s_currency}{s_gross_text}")

        if salary_lines:
            content_lines.append("\nЗАРПЛАТА:")
            content_lines.extend(salary_lines)

    # Work Conditions
    wc_lines = []
    for key, label in [
        ("employment_form", "Тип занятости"),
        ("required_experience", "Требуемый опыт"),
    ]:
        val = _format_value(data.get(key))
        if val:
            wc_lines.append(f"  {label}: {val}")

    work_format = _format_value(data.get("work_format", []))
    if work_format:
        wc_lines.append(f"  Формат работы: {work_format}")

    work_schedule = _format_value(data.get("work_schedule_by_days", []))
    if work_schedule:
        wc_lines.append(f"  График работы: {work_schedule}")

    if wc_lines:
        content_lines.append("\nУСЛОВИЯ РАБОТЫ:")
        content_lines.extend(wc_lines)

    # Description, Responsibility, Requirement
    for key, label in [
        ("job_description", "ОПИСАНИЕ ВАКАНСИИ"),
        ("responsibility", "ОБЯЗАННОСТИ"),
        ("requirement", "ТРЕБОВАНИЯ"),
    ]:
        text_content = _indent_text(data.get(key), "  ")
        if text_content:
            content_lines.append(f"\n{label}:")
            content_lines.append(text_content)

    # Additional flags
    additional_lines = []
    for key, label in [
        ("is_internship", "Стажировка"),
        ("has_test_task", "Есть тестовое задание"),
        ("accept_handicapped_employers", "Доступно для людей с инвалидностью"),
    ]:
        val = data.get(key)  # Keep as boolean or None
        if val is not None:  # Only add if key is present
            formatted_val = _format_value(val)
            additional_lines.append(f"  {label}: {formatted_val}")
    if additional_lines:
        content_lines.append("\nДОПОЛНИТЕЛЬНО:")
        content_lines.extend(additional_lines)

    # Contacts
    contacts = data.get("contacts", {})
    if isinstance(contacts, dict) and contacts:
        contact_lines = []
        name = _format_value(contacts.get("name"))
        if name:
            contact_lines.append(f"  Контактное лицо: {name}")
        email = _format_value(contacts.get("email"))
        if email:
            contact_lines.append(f"  Email: {email}")

        phones = contacts.get("phones", [])
        if isinstance(phones, list) and phones:
            phone_numbers = []
            for p in phones:
                if isinstance(p, dict):
                    formatted_phone = _format_value(p.get("formatted"))
                    if formatted_phone:
                        phone_numbers.append(formatted_phone)
            if phone_numbers:
                contact_lines.append(f"  Телефоны: {', '.join(phone_numbers)}")

        if contact_lines:
            content_lines.append("\nКОНТАКТЫ:")
            content_lines.extend(contact_lines)

    # Details
    details_lines = []

    prof_roles = _format_value(data.get("professional_roles", []))
    if prof_roles:
        details_lines.append(f"  Профессиональные роли: {prof_roles}")

    if details_lines:
        content_lines.append("\nДЕТАЛИ:")
        content_lines.extend(details_lines)

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
        ("metro", "Метро"),
    ]:
        val = _format_value(data.get(key))
        if val:
            sc_main_lines.append(f"  {label}: {val}")

    districts = _format_value(data.get("districts"))
    if districts:
        sc_main_lines.append(f"  Районы: {districts} (не участвуют в поиске)")

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
        "full": "Полная занятость",
        "part": "Частичная занятость",
        "project": "Проектная работа/разовое задание",
        "volunteer": "Волонтерство",
        "probation": "Стажировка",
    }
    selected_employment = _get_multiple_selected_options(data.get("employment", {}), employment_map)
    if selected_employment:
        sc_work_cond_lines.append(f"  Тип занятости: {selected_employment}")

    schedule_map = {
        "fullDay": "Полный день",
        "shift": "Сменный график",
        "flexible": "Гибкий график",
        "remote": "Удаленная работа",
        "flyInFlyOut": "Вахтовый метод",
    }
    selected_schedule = _get_multiple_selected_options(data.get("schedule", {}), schedule_map)
    if selected_schedule:
        sc_work_cond_lines.append(f"  График работы: {selected_schedule}")

    part_time_map = {
        "project": "Разовое задание или проект",
        "part": "Неполный день",
        "from_four_to_six_hours_in_a_day": "От 4 часов в день",
        "only_saturday_and_sunday": "По выходным",
        "start_after_sixteen": "По вечерам",
    }
    selected_part_time = _get_multiple_selected_options(data.get("part_time", {}), part_time_map)
    if selected_part_time:
        sc_work_cond_lines.append(f"  Подработка: {selected_part_time}")

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
    # Using the provided YAML content as Python dictionaries for demonstration
    resume_yaml_content = """
about_me: "Меня зовут Аристаний и я специализируюсь в области web-программирования\\
  \\ на Python.\\n\\nЛичные достижения:\\n- Победитель хакатона - Занял первое место в\\
  \\ хакатоне IT Inno Hack 2023\\n- Создатель популярного проекта mqtt-packet-parser\\
  \\ (собрал более 300 звезд на GitHub)\\n\\nВ список моих интересов входят:\\n- Чат-боты\\n\\
  \\  - Машинное обучение и искусственный интеллект\\n  - Computer Vision/CV/Компьютерное\\
  \\ зрение\\n  - Natural language processing/NLP/Обработка естественного языка\\n\\
  -\\ Кибербезопасность\\n  - Antifraud/Выявление мошеннических действий\\n\\nМои проекты:\\n\\
  - https://github.com/aristaniy93/client_int_bot.git\\nClient Interaction Telegram\\
  \\ Bot - Телеграм-бот на Aiogram для взаимодействия с клиентами\\n\\n- https://github.com/aristaniy93/mqtt_packet_parser.git\\n\\
  Модуль Node.js для анализа пакетов MQTT, эффективность анализа повышена на 40%\\n\\
  \\nКонтакты для связи:\\n\\nТелеграм: @Tatyan_kts\\nТел./WhatsApp:  + 7 920 305 74 98\\n\\
  Email: aristaniy93@gmail.com\\n"
availability:
  notice_period: 2 недели
certifications:
- achieved_at: '2024-01-01'
  title: Certified Associate in Python Programming
  type: custom
  url: https://www.pluralsight.com/cloud-guru/courses/certified-associate-in-python-programming-certification-pcap-31-03?clickid=EAIaIQobChMI482T9IaWigMVCpCDBx0HrgzdEAAYAyAAEgIS6fD_BwE&utm_source=google&utm_medium=paid-search&utm_campaign=upskilling-and-reskilling&utm_term=ssi-emea-dynamic&utm_content=free-trial&gad_source=1&gclid=EAIaIQobChMI482T9IaWigMVCpCDBx0HrgzdEAAYAyAAEgIS6fD_BwE
- achieved_at: '2023-01-01'
  title: Django Certified Solutions Architect
  type: custom
  url: https://www.tealhq.com/certifications/python-django-developer
education_details:
  additional:
  - name: Python разработчик
    organization: Яндекс Практикум
    result: Python разработчик
    year: 2021
  attestation:
  - name: PCPP1™ – Certified Professional Python Programmer Level 1
    organization: Python Institute
    result: Python Programmer
    year: 2024
  elementary:
  - name: Московский государственный технический университет имени Н.Э. Баумана (национальный
      исследовательский университет), Москва
    year: 2024
  level: Высшее
  primary:
  - education_level: Высшее
    name: Московский государственный университет имени М.В. Ломоносова, Москва
    organization: ВМК
    university_acronym: МГУ
    year: 2019
experience_details:
  details:
  - company: ООО «Green-Park»
    description: "Обязанности:\\n- разработка веб-платформы для промо-кампании\\n- разработка\\
      \\ телеграм-бота для промо-кампании\\n\\nДостижения:\\n      - Организовал структуру\\
      \\ проекта\\n      - Cоздал посадочную страницу на React, обеспечивающую UX/UI-оптимизацию\\
      \\ и взаимодействие с пользователем\\n      - Внедрил асинхронную обработку чеков\\
      \\ API Федеральной налоговой службы\\n      - Интегрировал API Яндекс Карт\\n \\
      \\     - Ускорил деплой на 10 минут благодаря Git + Docker-compose\\n      - Настроил\\
      \\ веб-сервер при помощи Nginx и Сertbot"
    industries: []
    position: Python разработчик
    start_date: '2022-08-01'
  - company: ПРАЙМ ГРУП
    description: "Обязанности:\\n- разработка телеграм-бота на Aiogram для взаимодействия\\
      \\ с клиентами\\n- создание сайта-сборника проектов на Django\\n\\nДостижения:\\n\\
      \\      - Разработал базу данных для хранения и обновления рабочего расписания\\n\\
      \\      - Внедрил систему мгновенных уведомлений, позволяющую оповещать клиентов\\
      \\ об изменениях в заказах в режиме реального времени\\n      - Интегрировал API\\
      \\ Яндекс Карт и Яндекс Погоды"
    end_date: '2022-06-01'
    industries: []
    position: Python разработчик
    start_date: '2020-09-01'
  total_experience_years: 4
general_knowledge_questions: ''
languages:
  Русский: Родной
personal_information:
  age: ''
  birthday: ''
  citizenship:
  - Россия
  current_city: Орел
  email: aristaniy93@gmail.com
  first_name: Аристаний
  has_vehicle: false
  last_name: Звяегольцев
  legal_authorization:
  - Россия
  linkedin: https://linkedin.com/in/aristaniy-zvyagoltsev-f3e57c712
  livejournal: https://aristaniy93.livejournal.com
  metro: ''
  middle_name: Астромерович
  moi_krug: https://moi-krug.ru/aristaniy93
  other_site: https://www.aristaniy93.ru
  phone: +7 (933) 575-35-35
  preferred_contact: email
  sex: Мужской
recommendation:
- contact: ''
  name: Михаил
  organization: ПРАЙМ ГРУП
  position: Генеральный директор
salary_expectations:
  amount: 300000
  currency: RUR
skills:
- Python
- SQL
- Linux
- PostgreSQL
- Git
- Django Framework
- Английский язык
- React
- Redis
- JavaScript
- Docker
- FastAPI
- Aiogram
- REST
- HTML
- Clickhouse
- CSS
- Celery
- RabbitMQ
- Unit Testing
- Apache Airflow
- Flask
work_preferences:
  can_relocate: не могу переехать
  employments:
  - Полная занятость
  position: Программист Python
  professional_roles:
  - Аналитик
  - Программист, разработчик
  ready_to_business_trips: не готов к командировкам
  schedules:
  - Полный день
  - Удаленная работа
  travel_time_to_work: Не более часа
"""
    resume_data = yaml.safe_load(resume_yaml_content)

    vacancy_yaml_content = """
accept_handicapped_employers: false
area: Алматы
company_id: '11327547'
company_name: Max Solutions
contacts:
  email: katerina.chevtaeva@maxplansolutions.com
  name: 'Чевтаева Екатерина '
  phones:
  - city: '938'
    comment: null
    country: '351'
    formatted: '351938780508'
    number: '780508'
employment_form: Полная
has_test_task: false
is_internship: true
job_description: 'Мы в настоящий момент ищем начинающего Full-stack Developer. В разработке
  будет:70% фронтенд / 30% бэкенд. Задачи:  Помощь в разработке сервисов с использованием
  FastAPI. Помощь в написании кода для обработки бизнес-данных на Python. Помощь в
  создании UI компонентов с использованием Mantine и NextJS. Помощь в соединении фронтенда
  и бэкэнда с использованием Supabase. Поддержка пользователей по внутренним ИТ запросам
  (выдача доступов, создание учетных записей и т. д.).  Требования:  Базовые знания
  и практический опыт работы с: Python (от 6 месяцев практики - понимание как работают
  фреймворки : pandas, numpy). FastAPI или аналогичными Python-фреймворками. TypeScript,
  Next.js, Mantine. Supabase (или опыт работы с другими BaaS/Backend-as-a-Service).
  Понимание принципов REST-API. Основы работы с Git. Общая грамотность в написании
  документации и комментариев к коду. Проактивность, желание учиться и развиваться
  в full-stack направлении. Английский язык.  Будет плюсом:  Понимание как работают
  системы планирования и моделирования бизнес-процессов: Anapla, Optimacros, Casplan.
  Начальный опыт с аналитическими платформами и BI-инструментами. Понимание основ
  и принципов работы с Docker.  Условия:  Формат работы - удалённо (предпочтительно
  в часовом поясе UTC+5, по возможности в Астане для проведения периодических очных
  встреч). Возможность обучения у опытных разработчиков и участия в реальных проектах.
  Полный рабочий день - 40 часов в неделю. Доступ к внутренним образовательным материалам
  и курсам.  Для связи, пожалуйста, пишите: https://t.me/hr_CS_developers.'
job_title: Junior Full Stack
professional_roles:
- Программист, разработчик
required_experience: Нет опыта
requirement: 'Базовые знания и практический опыт работы с: Python (от 6 месяцев практики
  - понимание как работают фреймворки : pandas, numpy). '
responsibility: Помощь в разработке сервисов с использованием FastAPI. Помощь в написании
  кода для обработки бизнес-данных на Python. Помощь в создании...
salary:
  currency: KZT
  from: 300000
  gross: false
  to: 400000
vacancy_id: '121118419'
work_format:
- Удалённо
work_schedule_by_days:
- 5/2
"""
    vacancy_data = yaml.safe_load(vacancy_yaml_content)

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
metro: Павелецкая, Новокосино, Комсомольская
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
  full: true
  part: true
  project: false
  volunteer: false
  probation: false
schedule:
  fullDay: true
  shift: false
  flexible: false
  remote: true
  flyInFlyOut: false
part_time:
  project: true
  part: true
  from_four_to_six_hours_in_a_day: false
  only_saturday_and_sunday: false
  start_after_sixteen: false
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
user_id: '168901459'
max_applies_num: 100
tariff: 14days
"""
    search_config_data = yaml.safe_load(search_config_yaml_content)

    print("--- Human-Readable Resume (Full) ---")
    print(transform_resume_data(resume_data))
    print("\n\n--- Human-Readable Vacancy (Full) ---")
    print(transform_vacancy_data(vacancy_data))
    print("\n\n--- Human-Readable Search Config (Full) ---")
    print(transform_search_config_data(search_config_data))

    # Example with missing/empty data
    print("\n\n--- Example with Minimal Resume Data ---")
    minimal_resume_data = {
        "personal_information": {
            "first_name": "Иван",
            "email": "ivan@example.com",
            "age": "",  # Test empty string
        },
        "skills": ["Python", None, "", "SQL  "],  # Test filtering
        "experience_details": {
            "details": [
                {
                    "company": "MinimalCorp",
                    "description": None,  # Test None description
                }
            ]
        },
    }
    print(transform_resume_data(minimal_resume_data))

    print("\n\n--- Example with Minimal Vacancy Data ---")
    minimal_vacancy_data = {
        "job_title": "Developer",
        "company_name": " ",  # Test whitespace only
        "salary": {"currency": "USD"},
        "contacts": {"phones": [{"formatted": ""}]},  # Test empty formatted phone
    }
    print(transform_vacancy_data(minimal_vacancy_data))

    print("\n\n--- Example with Minimal Search Config Data ---")
    minimal_search_config_data = {
        "job_title": "Python Dev",
        "currency": {"RUR": True, "USD": False},  # RUR should be picked
        "experience": {"noExperience": True},
        "cover_letter": "",  # test explicitly empty cover letter
        "search_field": {"name": True},  # only name is true
    }
    print(transform_search_config_data(minimal_search_config_data))

    print("\n\n--- Example with completely empty data dict ---")
    print("Resume (empty dict):", transform_resume_data({}))
    print("Vacancy (empty dict):", transform_vacancy_data({}))
    print("Search Config (empty dict):", transform_search_config_data({}))

    print("\n\n--- Example with non-dict or None data ---")
    print("Resume (None):", transform_resume_data(None))
    print("Vacancy (string):", transform_vacancy_data("not a dict"))
    print("Search Config (None):", transform_search_config_data(None))
