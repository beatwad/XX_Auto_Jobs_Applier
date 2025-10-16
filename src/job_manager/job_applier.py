import os
import re
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager

from src.app_config import (
    COVER_LETTER_MODE,
    MINIMUM_WAIT_TIME_SEC,
    MONKEY_MODE,
    RESUME_MODE,
    SKILL_STAT_MODE,
)
from src.constants import LAST_RUN_FILE, SEARCH_CONFIG_FILE
from src.job_manager.authenticator import Authenticator
from src.logger_config import logger
from src.telegram.telegram_manager import TelegramReportSender
from src.utils.utils import (
    chrome_browser_options,
    enter_text,
    load_yaml_file,
    pause,
    save_yaml_file,
    scroll_slow,
    sleep,
)

search_config = load_yaml_file(SEARCH_CONFIG_FILE)
FIXED_COVER_LETTER = search_config.get("cover_letter")
MAX_APPLIES_NUM = 100


class JobApplier:
    """Класс для поиска и рассылки откликов работодателям"""

    def __init__(self, api: Any, resume_component: Any, search_component: Any):
        logger.info("Инициализация JobApplier")
        self.api = api
        self.resume_component = resume_component
        self.search_component = search_component
        self.gpt_answerer = None
        self.jobs_no_info = []  # вакансии, на которые не откликнулись из-за отсутствия информации
        self.driver = None
        self.resume_recommendations = ""
        self.job_key_skills = []  # ключевые навыки по мнению работодателя
        self.page_num = 0
        self.resume_vac_page_num = -1  # количество страниц с вакансиями, похожими на резюме
        self.error_num = 0
        self.total_applies_num = 0
        logger.info("JobApplier успешно инициализирован")

    def set_parameters(self, parameters: Dict[str, Any]):
        """Установка параметрок поиска"""
        logger.info("Установка параметров JobApplier")
        self.user_id = parameters["user_id"]
        self.hh_login = parameters.get("hh_login", "")
        self.hh_password = parameters.get("hh_password", "")
        self.resume_id = parameters["resume_id"]
        self.resume_titles = parameters["resume_titles"]
        # загрузка обязательных параметров
        self.job_title = self.resume_component.job_title
        self.max_applies_num = parameters.get("max_applies_num", MAX_APPLIES_NUM)
        self.max_total_applies_num = parameters.get("max_total_applies_num", 1500)
        # загрузить дополнительные настройки поиска
        self.apply_once_at_company = parameters.get("apply_once_at_company", True)
        self.skip_companies_with_test = parameters.get("skip_companies_with_test", False)
        self.fixed_cover_letter = parameters.get("cover_letter", None)
        # загрузить черный список компаний
        self.job_blacklist = parameters.get("job_blacklist", [])
        if self.job_blacklist:
            self.job_blacklist = [self._sanitize_text(j_b) for j_b in self.job_blacklist]
        # загрузить компании, в которые были успешно отправлены заявки
        self.success_companies = self._load_companies_from_yaml("success.yaml")
        # загрузить компании, в которые заявки отправлены не были
        self.skipped_companies = self._load_companies_from_yaml("skipped.yaml")
        # загрузить компании, в которые заявки отправлены не были по причине программной ошибки
        self.failed_companies = self._load_companies_from_yaml("failed.yaml")
        # загрузить список вопросов, на которые уже были даны ответы
        self.seen_answers = self._load_data_from_yaml("answers.yaml")
        # загрузить статистику по самым востребованным навыкам в вакансиях
        self.skill_stat = self._load_data_from_yaml("skill_stat.yaml")
        # загрузить кэш с информацией о последнем поиске
        self.cache = self._load_cache()
        self.applies_num = 0
        self.previous_apply_number = self._check_the_previous_apply_number()
        self.success_applies_num = self.previous_apply_number
        self.total_applies_num = self.cache.get("total_applies_num", 0)
        logger.info("Параметры успешно установлены")

    def set_gpt_answerer(self, gpt_answerer: Any):
        """
        Задать LLM для ответов на вопросы и написания
        сопроводительных писем
        """
        self.gpt_answerer = gpt_answerer

    def set_resume(self, resume: Dict[str, Any]) -> None:
        """Добавляем резюме для анализа."""
        self.resume = resume

    def set_resume_generator_manager(
        self, resume_generator_manager: Any, gpt_resume_generator: Any
    ):
        """
        Задать менеджер для написания резюме
        """
        self.resume_generator_manager = resume_generator_manager
        self.gpt_resume_generator = gpt_resume_generator

    def search_vacancies(self, page_num: int = 0) -> List[Any]:
        """Начать поиск"""
        search_params = {"page": page_num, "per_page": 10}
        vacancies = []
        for key, value in self.search_component.search_params.items():
            if value:
                search_params[key] = value
        # сначала ищем вакансии, похожие на данное резюме,
        if self.resume_vac_page_num == -1:
            resume_vacancies = self.api.api_request(
                f"https://api.hh.ru/resumes/{self.resume_id}/similar_vacancies",
                params=search_params,
            )
            # если не нашли - записываем общее количество страниц с вакансиями, похожими на резюме
            if len(resume_vacancies["items"]) == 0:
                self.resume_vac_page_num = page_num
            else:
                vacancies = resume_vacancies["items"]
        # обращаемся сюда только в случае, если только начали поиск или
        # уже обработали все вакансии, похожие на резюме
        if page_num == 0 or self.resume_vac_page_num > -1:
            search_params_ = search_params.copy()
            search_params_["page"] = page_num - max(self.resume_vac_page_num, 0)
            search_params_["text"] = self.job_title
            main_vacancies = self.api.api_request(
                "https://api.hh.ru/vacancies",
                params=search_params_,
            )
            if self.resume_vac_page_num > -1:
                vacancies = main_vacancies["items"]
        # выводим общее количество всех найденных вакансий, если только начали поиск
        if page_num == 0 and self.resume_vac_page_num == -1:
            total_found = resume_vacancies["found"] + main_vacancies["found"]
            logger.info(f"Найдено {total_found} вакансий")
        return vacancies

    def scrape_vacancy(self, vacancy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Собрать всю информацию о работодателе
        для дальнейшей передачи в LLM
        """
        job = {}
        job["job_title"] = vacancy["name"]
        job["vacancy_id"] = vacancy["id"]
        job["company_id"] = vacancy["employer"].get("id")
        if vacancy.get("salary"):
            job["salary"] = vacancy["salary"]
        if vacancy.get("address"):
            job["address"] = vacancy["address"]
        job["area"] = vacancy["area"]["name"]
        if vacancy.get("contacts"):
            job["contacts"] = vacancy["contacts"]
        if vacancy.get("department"):
            job["company_department"] = vacancy["department"]["name"]
        job["company_name"] = vacancy["employer"]["name"]
        if vacancy["employer"].get("accredited_it_employer"):
            job["accredited_it_employer"] = vacancy["employer"]["accredited_it_employer"]
        job["has_test_task"] = vacancy["has_test"]
        if vacancy["snippet"]["requirement"]:
            job["requirement"] = vacancy["snippet"]["requirement"]
        if vacancy["snippet"]["responsibility"]:
            job["responsibility"] = vacancy["snippet"]["responsibility"]
        if vacancy.get("work_format"):
            job["work_format"] = [format["name"] for format in vacancy["work_format"]]
        if vacancy.get("work_schedule_by_days"):
            job["work_schedule_by_days"] = [
                schedule["name"] for schedule in vacancy["work_schedule_by_days"]
            ]
        if vacancy.get("employment_form"):
            job["employment_form"] = vacancy["employment_form"]["name"]
        if vacancy.get("experience"):
            job["required_experience"] = vacancy["experience"]["name"]
        job["professional_roles"] = [role["name"] for role in vacancy["professional_roles"]]
        if vacancy.get("night_shifts"):
            job["night_shifts"] = vacancy["night_shifts"]
        if vacancy.get("internship"):
            job["is_internship"] = vacancy["internship"]
        if vacancy.get("accept_temporary"):
            job["accept_temporary_employment"] = vacancy["accept_temporary"]
        # собрать дополнительную информацию о работодателе (описание)
        vacancy_description = self.api.api_request(
            f"https://api.hh.ru/vacancies/{vacancy['id']}",
        )
        job_description = vacancy_description["description"]
        job["job_description"] = re.sub(r"<[^>]+>", "", job_description)
        job["accept_handicapped_employers"] = vacancy_description["accept_handicapped"]
        if vacancy_description.get("driver_license_types"):
            job["required_driver_licenses"] = vacancy_description["driver_license_types"]
        if vacancy_description.get("key_skills"):
            self.job_key_skills = [v["name"] for v in vacancy_description["key_skills"]]
        else:
            self.job_key_skills = []
        return job

    def resume_improvement_recommendations(self) -> None:
        """
        Пишем рекомендации по улучшению резюме
        """
        resume_recommendations = self._load_data_from_yaml("resume_recommendations.yaml")
        # если файл с рекомендациями еще не создан - пишем рекомендации по улучшению резюме
        # и сохраняем их в файл
        if not resume_recommendations:
            self.resume_recommendations = self.gpt_answerer.resume_improvement_recommendations()
            self.resume_recommendations = self.resume_component.deanonymize_personal_information(
                self.resume_recommendations
            )
            self._save_data_to_yaml(self.resume_recommendations, "resume_recommendations.yaml")

    def start_applying(self) -> None:
        """Разослать отклики всем работодателям на всех страницах"""

        # определяем время старта поиска
        if self.cache.get("last_run"):
            last_run = datetime.fromisoformat(self.cache["last_run"])
            # если это не первый запуск - увеличиваем время последнего поиска на 24 часа
            # и записываем его как последний поиск (во избежание дрейфа времени запуска программы)
            self.cache["last_run"] = (last_run + timedelta(hours=24)).isoformat()
        else:
            last_run = datetime.now().isoformat()
            self.cache["last_run"] = last_run
        result = ""
        # пишем рекомендации по улучшению резюме
        self.resume_improvement_recommendations()
        # продолжаем пока не достигнем максимально допустимого числа откликов
        while self.success_applies_num < self.max_applies_num and self.applies_num < 400:
            # идем по всем страницам пока они не закончатся
            vacancies = self.search_vacancies(self.page_num)
            if len(vacancies) == 0:
                if self.page_num == 1:
                    logger.warning("По данному поисковому запросу не найдено ни одной вакансии")
                break
            for vacancy in vacancies:
                url = vacancy.get("alternate_url")
                try:
                    result = self.send_repsonse(vacancy)
                    if result == "Limit":
                        logger.warning("Достигнуто максимально допустимое число откликов")
                        break
                except Exception:
                    tb_str = traceback.format_exc()
                    logger.error(f"Неизвестная ошибка на странице: {url}\n{tb_str}")
                    # счетчик повторных ошибок, если пришло слишком много ошибок подряд -
                    # выходим из программы и шлем уведомление
                    if self.error_num == MAX_APPLIES_NUM:
                        logger.error(
                            f"Критическое количество идущих подряд ошибок {MAX_APPLIES_NUM}"
                        )
                        result = "Error"
                        break
                    else:
                        self.error_num += 1
                    continue
                else:
                    self.error_num = 0
            # прерываем поиск вакансий, если достигнут лимит
            if result == "Limit" or result == "Error":
                break
            self.page_num += 1
            logger.info(f"Переходим на страницу {self.page_num}")
        logger.info(f"Откликов отправлено: {self.success_applies_num}")
        logger.info("Завершаем работу.")
        # если поиск прошел успешно - отсылаем отчет о проделанной работе
        if (
            not (COVER_LETTER_MODE is True or SKILL_STAT_MODE is True or RESUME_MODE is True)
            and result != "Error"
        ):
            # если хотя бы на одну вакансию откликнулись успешно c момента запуска
            # записываем время последнего поиска и отсылаем отчет
            if self.previous_apply_number < self.success_applies_num:
                logger.info("Отсылаем отчёт о проделанной работе в Telegram")
                self.send_report()
                self._write_the_last_search_time()

    def send_repsonse(self, vacancy: Dict[str, Any]) -> str:
        """Разослать отклики всем работодателям на странице"""
        # собрать описание вакансии
        job = self.scrape_vacancy(vacancy)
        minimum_job_time = time.time() + MINIMUM_WAIT_TIME_SEC
        company_name = job["company_name"]
        company_job_title = job["job_title"]
        logger.info(f"Найдена вакансия {company_job_title}")
        # если вакансия еще не встречалась и компания не в черном списке
        # - начать процесс отклика на вакансию
        if self._is_blacklisted(self._sanitize_text(company_name)):
            apply_result = "Skip", "Вакансия в черном списке"
            logger.warning("Вакансия в черном списке, пропускаем")
            pause(1, 2)
        # elif not job["has_test_task"]:
        #     logger.warning("Вакансия без теста")
        #     apply_result = (
        #         "Skip",
        #         "Вакансия не имеет тестовое задание",
        #     )
        #     pause(1, 2)
        elif (not self.hh_login or not self.hh_password) and job["has_test_task"]:
            apply_result = (
                "Skip",
                "Вакансия имеет тестовое задание и нет возможности обрабатывать такие вакансии",
            )
            logger.warning(
                "Вакансия имеет тестовое задание и нет возможности обрабатывать такие вакансии"
            )
            self._collect_job_info(company_job_title, vacancy["alternate_url"], apply_result[1])
            pause(1, 2)
        else:
            is_applied, reason = self._is_already_applied_to_job_or_company(job)
            if is_applied:
                apply_result = "Skip", reason
                logger.warning(f"Пропускаем вакансию по причине: {reason}")
                pause(1, 2)
            else:
                # задать вакансию в LLM для оценки
                self.gpt_answerer.set_job(job)
                if MONKEY_MODE is True:
                    # в 'режиме обезьяны' любая вакансия считается интересной
                    job_is_interesting = True
                else:
                    # иначе просить LLM оценить, является ли вакансия интересной или нет
                    job_is_interesting = self.gpt_answerer.job_is_interesting()
                # откликнуться на вакансию только если она интересна
                if job_is_interesting:
                    # обновляем список требуемых для вакансии навыков только если сама вакансия интересна
                    self._update_skill_stat(self.job_key_skills)
                    apply_result = self.apply_job(vacancy, company_name, company_job_title, job)
                    result, reason = apply_result
                    # если вакансия пропускается по причине отсутствия информации, добавить ее в список вакансий,
                    # информация о которых потом будет отправлена клиенту
                    if result == "Skip" and reason.startswith("Не смогли"):
                        self._collect_job_info(company_job_title, vacancy["alternate_url"], reason)
                elif job_is_interesting is None:
                    apply_result = "Error", "Ошибка при вызове LLM."
                else:
                    apply_result = "Skip", "Вакансия не интересна"
                    logger.debug("Вакансия не интересна, пропускаем")
        result, _ = apply_result
        # если находимся в одном из режимов сбора информации - не ведем статистику по вакансиям
        if COVER_LETTER_MODE is True or SKILL_STAT_MODE is True or RESUME_MODE is True:
            return "OK"
        # увеличиваем счетчики всех откликов и успешных откликов
        self.applies_num += 1
        if result == "Success":
            self.success_applies_num += 1
            self.total_applies_num += 1
            self.cache["success_applies_num"] = self.success_applies_num
            self.cache["total_applies_num"] = self.total_applies_num
            self.cache["last_apply"] = datetime.now().isoformat()
            self._write_the_last_search_time()
            logger.info(
                f"Количество вакансий, на которые успешно откликнулись: {self.success_applies_num}"
            )
            logger.info(f"Общее количество успешных откликов: {self.total_applies_num}")
        if result != "Limit":
            self._save_company(job, apply_result, vacancy)
        # если страница была обработана быстрее, чем за минимальное время -
        # подождать, пока это время не закончится
        time_left = int(minimum_job_time - time.time())
        if time_left > 0:
            sleep((time_left, time_left + 5))
        # если наткнулись на лимит по вакансиям - прекращаем отклик
        if result == "Limit":
            return "Limit"
        stop_reason = ""
        if self.success_applies_num >= self.max_applies_num:
            stop_reason = f"Достигнуто максимально допустимое число откликов за запуск: {self.success_applies_num}/{self.max_applies_num}"
        elif (
            self.max_total_applies_num is not None
            and self.total_applies_num >= self.max_total_applies_num
        ):
            stop_reason = f"Достигнут общий лимит откликов: {self.total_applies_num}/{self.max_total_applies_num}"

        if stop_reason:
            logger.info(stop_reason)
            return "Limit"
        return result

    def apply_job(
        self, vacancy: Dict[str, Any], company_name: str, job_title: str, job: dict
    ) -> Tuple[str, str]:
        """Откликнуться на вакансию"""
        try:
            if self.fixed_cover_letter:
                logger.info(f"Берем готовое сопроводительное письмо:\n'{self.fixed_cover_letter}'")
                cover_letter_text = self.fixed_cover_letter
            elif not RESUME_MODE and not SKILL_STAT_MODE:
                cover_letter_text = self.gpt_answerer.write_cover_letter()
                # деанонимизируем информацию
                cover_letter_text = self.resume_component.deanonymize_personal_information(
                    cover_letter_text
                )
                self._save_cover_letter(company_name, cover_letter_text, vacancy["alternate_url"])
            if COVER_LETTER_MODE is True:
                # если находимся в режиме написания сопровод. писем - не откликаемся на вакансии,
                # только сохраняем сгенерированные сопроводительные письма в файл
                logger.info(
                    "Находимся в режиме отладки сопрводительных писем - не откликаемся на вакансии"
                )
            elif SKILL_STAT_MODE is True:
                # если находимся в режиме сбора статистики по навыкам - не откликаемся на вакансии,
                # только сохраняем статистику по навыкам в файл
                logger.info(
                    "Находимся в режиме сбора статистики по навыкам - не откликаемся на вакансии"
                )
            elif RESUME_MODE is True:
                # если находимся в режиме резюме - не откликаемся на вакансии,
                # только сохраняем сгенерированные резюме
                logger.info("Находимся в режиме резюме - не откликаемся на вакансии")
                self.write_and_upload_resume(job, vacancy["alternate_url"])
            else:
                params = {
                    "message": cover_letter_text,
                    "resume_id": self.resume_id,
                    "vacancy_id": vacancy["id"],
                }
                response = self.api.api_request(
                    type_="post",
                    url="https://api.hh.ru/negotiations",
                    params=params,
                )
                if "response_text" in response and "<!doctype html>" in response["response_text"]:
                    return (
                        "Skip",
                        "Не смогли откликнуться. При отклике предлагают переход на сторонний сайт",
                    )

                if "errors" in response:
                    errors = response["errors"]
                    for error in errors:
                        # если уперлись в лимит по количеству откликов - выходим из цикла
                        if error["value"] == "limit_exceeded":
                            logger.warning("Достигли лимита откликов")
                            return "Limit", ""
                        # если нашли вопросы - отвечаем
                        if error["value"] == "test_required" and self.hh_login and self.hh_password:
                            logger.info("Для отклика требуется пройти тест")
                            self.driver = self.init_driver()
                            answer_result, answer_text = self.find_and_handle_questions(
                                vacancy, cover_letter_text
                            )
                            if self.driver is not None:
                                self.driver.close()
                                self.driver = None
                            # если не на все вопросы были найдены ответы - пропускаем вакансию
                            if not answer_result:
                                return "Skip", answer_text
                            logger.info(f"Успешно откликнулись на вакансию компании {company_name}")
                            return "Success", ""
                    # если ошибка заключается в другом, пропускаем вакансию
                    error_message = ";".join([error["value"] for error in errors])
                    logger.warning(
                        f"Пропускаем вакансию компании {company_name} по причине ошибки при отклике: {error_message}"
                    )
                    return "Skip", error_message
                logger.info(f"Успешно откликнулись на вакансию компании {company_name}")
            pause()
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(
                f"Неизвестная ошибка на странице {vacancy['alternate_url']} во время отклика на вакансию {job_title} компании {company_name}\n{tb_str}"
            )
            if self.driver is not None:
                self.driver.close()
                self.driver = None
            return "Error", str(e)
        return "Success", ""

    def init_driver(self) -> webdriver.Chrome:
        """Инициализировать Selenium driver"""
        try:
            options = chrome_browser_options()
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception:
            tb_str = traceback.format_exc()
            raise RuntimeError(f"Failed to initialize browser: {tb_str}")

    def find_and_handle_questions(
        self, vacancy: Dict[str, Any], cover_letter_text: str
    ) -> Tuple[bool, str]:
        """Если на странице есть вопросы - использовать LLM для ответа на них"""
        authenticator = Authenticator(self.driver)
        authenticator.set_parameters(self.hh_login, self.hh_password)
        # заходим на сайт
        result = authenticator.start()
        if not result:
            logger.warning("Не смогли зайти на сайт")
            if self.driver is not None:
                self.driver.close()
                self.driver = None
            return False, "Не смогли зайти на сайт"
        self.driver.get(f"https://hh.ru/applicant/vacancy_response?vacancyId={vacancy['id']}")
        pause(2, 3)
        # обрабатываем сообщения, которые мешают отклику на вакансию
        self._handle_interfering_messages()
        # отвечаем на вопросы
        question_element = ("xpath", "//*[@data-qa='task-body']")
        questions = self.driver.find_elements(*question_element)
        if questions:
            logger.info("Нашли вопрос(ы).")
            for question in questions:
                answer, answer_text = self.handle_question(question)
                if not answer:
                    logger.warning("Прерываем отклик на вакансию.")
                    return False, answer_text
        else:
            logger.warning("Вопросы не найдены.")
            return False, "Вопросы не найдены."
        # обрабатываем сообщения, которые мешают отклику на вакансию
        self._handle_interfering_messages()
        # выбираем нужное резюме
        answer, answer_text = self._select_correct_resume()
        if not answer:
            return False, answer_text
        # вводим текст сопроводительного письма
        answer, answer_text = self._enter_cover_letter(cover_letter_text)
        if not answer:
            return False, answer_text
        # обрабатываем сообщения, которые мешают отклику на вакансию
        self._handle_interfering_messages()
        # жмем кнопку 'Откликнуться'
        apply_element = self.driver.find_elements("xpath", "//*[text()='Откликнуться']")
        if not apply_element:
            logger.error("Не нашли кнопку отклика")
            return False, "Не нашли кнопку отклика"
        scroll_slow(self.driver, apply_element[0])
        apply_element[0].click()
        pause(3, 5)
        return True, ""

    def handle_question(self, question: WebElement) -> Tuple[bool, str]:
        """
        Метод для определения типа вопроса и выбора соответствующего
        подметода для ответа на данный вопрос
        """
        radio_fields = question.find_elements("xpath", ".//*[@data-qa='radio-container']")
        if radio_fields:
            return self._handle_radio_question(question, radio_fields)

        checkbox_fields = question.find_elements("xpath", ".//*[@data-qa='checkbox-container']")
        if checkbox_fields:
            return self._handle_checkbox_question(question, checkbox_fields)

        text_fields = question.find_elements("xpath", ".//textarea")
        if text_fields:
            return self._handle_textbox_question(question, text_fields[0])

        output = f"Не найдено поля для ввода текста или вариантов ответа на вопрос {question.text}"
        logger.error(output)
        return False, output

    def send_report(self) -> None:
        """
        После завершения рассылки резюме послать отчет, который будет содержать
        количество вакансий, на которые приложения откликнулось, список вакансий,
        на которые приложение по той или иной причине откликнуться не смогло,
        а также рекомендации по улучшению резюме
        """
        bot = TelegramReportSender()
        bot.send_telegram_report(
            self.hh_login,
            self.resume,
            self.success_applies_num,
            self.jobs_no_info,
            self.skill_stat,
            self.resume_recommendations,
            self.resume_component,
        )

    def _load_cache(self) -> Dict[str, str]:
        """Загружаем кэш из файла"""
        try:
            with open(LAST_RUN_FILE, "r") as f:
                cache = yaml.safe_load(f) or {}
                return cache
        except Exception:
            logger.warning("Не удалось загрузить кэш из локального файла")
            return {}

    def check_the_last_search_time(self) -> bool:
        """
        Проверяем, чтобы поиск работы запускался не раньше,
        чем через сутки после предыдущего запуска.
        Либо проверяем, что последний отклик был меньше часа назад
        это означает, что приложение принудительно перезапускали.
        """
        logger.info("Проверяем время запуска предыдущего поиска")
        if self.cache.get("last_run"):
            last_run = datetime.fromisoformat(self.cache["last_run"])
        else:
            return True
        if (
            datetime.now() - last_run
        ).total_seconds() >= 60 * 60 * 24 or self.previous_apply_number > 0:
            return True
        return False

    def _check_the_previous_apply_number(self) -> bool:
        """
        Проверяем, были ли отклики без завершенного поиска.
        Если да, то возвращаем их количество
        """
        logger.info("Проверяем время последнего отклика")
        if self.cache.get("last_apply"):
            last_apply = datetime.fromisoformat(self.cache["last_apply"])
        else:
            return 0
        # Если предыдущий поиск не был завершен, а значит с момента последнего отклика прошло меньше часа,
        # то мы считаем с начиная с предыдущего количества откликов
        if (datetime.now() - last_apply).total_seconds() < 59 * 60:
            prev_apply_num = self.cache.get("success_applies_num", 0)
            return prev_apply_num
        return 0

    def _write_the_last_search_time(self) -> None:
        """
        Записываем время последнего поиска работы
        """
        save_yaml_file(LAST_RUN_FILE, self.cache)
        cache_path = self._define_output_file("last_run.yaml")
        try:
            save_yaml_file(cache_path, self.cache)
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при сохранении информации о последнем поиске\n{tb_str}")

    def _collect_job_info(self, company_job_title: str, job_link: str, reason: str) -> None:
        """Добавить информацию о вакансии в список вакансий для последующей отправки отчета клиенту"""
        job_info = {
            "job_title": company_job_title,
            "link": job_link,
            "reason": reason,
        }
        self.jobs_no_info.append(job_info)

    def _enter_cover_letter(self, cover_letter_text: str) -> Tuple[bool, str]:
        """Вставить текст сопроводительного письма"""
        cover_letter_button = self.driver.find_elements("xpath", "//*[text()='Добавить']")
        if cover_letter_button:
            scroll_slow(self.driver, cover_letter_button[0])
            cover_letter_button[0].click()
            pause()
        else:
            logger.warning("Не нашли кнопку сопроводительного письма")
        cover_letter_text_field = self.driver.find_elements(
            "xpath", "//*[@data-qa='vacancy-response-popup-form-letter-input']"
        )
        if not cover_letter_text_field:
            logger.error("Не нашли поле ввода сопроводительного письма")
            return False, "Не нашли поле ввода сопроводительного письма"
        scroll_slow(self.driver, cover_letter_text_field[0])
        logger.info("Вводим текст сопроводительного письма")
        cover_letter_text_field[0].send_keys(cover_letter_text)
        return True, ""

    def _select_correct_resume(self) -> Tuple[bool, str]:
        """Выбор подходящего резюме"""
        # если подходящее резюме уже выбрано - продолжаем
        suitable_elements = self.driver.find_elements(
            "xpath", "//*[@data-qa='cell-text' or @data-qa='resume-title']"
        )
        for element in suitable_elements:
            if element.text == self.job_title:
                logger.info("Выбрано правильное резюме, продолжаем")
                return True, ""
        # прокликать все подходящие элементы
        # и если на странице появится подходящее резюме - кликнуть на него
        for element in suitable_elements:
            if element.text not in self.resume_titles:
                continue
            try:
                element.click()
            except ElementNotInteractableException:
                pause()
                continue
            pause()
            resume_to_click = self.driver.find_elements("xpath", f"//*[text()='{self.job_title}']")
            if resume_to_click:
                resume_to_click[0].click()
                logger.info("Выбираем правильное резюме")
                return True, ""
        logger.error("Не нашли нужное резюме")
        return False, "Не нашли нужное резюме"

    def _handle_radio_question(
        self, question: WebElement, radio_fields: List[WebElement]
    ) -> Tuple[bool, str]:
        """Метод для ответа на вопрос с возможностью выбора одной опции"""
        scroll_slow(self.driver, question)
        question_text = question.text
        logger.info(f"Нашли вопрос c выбором одного ответа: {question_text}")
        options = [
            radio_field.find_element("xpath", "../..").text for radio_field in radio_fields
        ] + ["No info"]
        answer = self.gpt_answerer.select_one_answer_from_options(question_text, options)
        # Находим и отмечаем подходящий вариант ответа
        for idx, option in enumerate(options):
            if option == answer and option != "No info":
                scroll_slow(self.driver, radio_fields[idx])
                radio_fields[idx].click()
                pause()
                return True, ""

        output = f"Не нашли ни одного подходящего ответа на вопрос {question.text}"
        logger.warning(output)
        return False, output

    def _handle_checkbox_question(
        self, question: WebElement, checkbox_fields: List[WebElement]
    ) -> Tuple[bool, str]:
        """Метод для ответа на вопрос с возможностью выбора нескольких опций"""
        scroll_slow(self.driver, question)
        question_text = question.text
        logger.info(f"Нашли вопрос c выбором множества ответов: {question_text}")
        options = [
            checkbox_field.find_element("xpath", "../..").text for checkbox_field in checkbox_fields
        ] + ["No info"]
        answers = self.gpt_answerer.select_many_answers_from_options(question_text, options)
        # Находим и отмечаем все подходящие варианты ответа
        result = False
        for idx, option in enumerate(options):
            if option in answers and option != "No info":
                scroll_slow(self.driver, checkbox_fields[idx])
                checkbox_fields[idx].click()
                result = True
                pause()

        if result:
            return True, ""

        output = f"Не нашли ни одного подходящего ответа на вопрос {question.text}"
        logger.warning(output)
        return False, output

    def _handle_textbox_question(
        self, question: WebElement, text_field: WebElement
    ) -> Tuple[bool, str]:
        """Метод для ответа на текстовый вопрос"""
        scroll_slow(self.driver, question)
        question_text = question.text
        logger.info(f"Нашли текстовый вопрос: {question_text}")

        # поискать ответ в файле сохраненных предыдущих ответов
        existing_answer = None
        sanitized_question = self._sanitize_text(question_text)
        for answer in self.seen_answers:
            if self._sanitize_text(answer["question"]) == sanitized_question:
                existing_answer = answer["answer"]
                logger.info(f"Найден готовый ответ: {existing_answer}")
                break

        if existing_answer:
            answer = existing_answer
            logger.info(f"Используем готовый ответ: {answer}")
        else:
            answer = self.gpt_answerer.answer_question_textual_wide_range(question_text)
            if answer.startswith(
                "Вопрос не принадлежит ни к одной из известных тем, возвращаем пустой ответ."
            ):
                output = f"Не смогли определить тип вопроса: {question_text}"
                logger.warning(output)
                return False, output
            if (
                "no info" in answer.lower()
                or "нет информации" in answer.lower()
                or "не указан" in answer.lower()
            ):
                output = f"Не смогли ответить на вопрос: {question_text}"
                logger.warning(output)
                return False, output
            logger.info(f"Сгенерирован ответ: {answer}")
            self.seen_answers.append({"question": question_text, "answer": answer})
            # сохранить новый ответ в файл
            self._save_data_to_yaml(self.seen_answers, "answers.yaml")
            logger.info("Тестовый вопрос сохранен в YAML.")

        pause()
        # деанонимизируем данные в ответе перед их вводом в поле для ответа
        answer = self.resume_component.deanonymize_personal_information(answer)
        enter_text(text_field, answer)
        logger.info("Ответ введен в textbox")
        return True, ""

    def _handle_interfering_messages(self) -> None:
        """
        Обработать сообщения, которые мешают отклику на вакансию
        (например, сообщение с cookies, уведомления и пр.)
        """
        cookies_message = self.driver.find_elements("xpath", "//*[text()='Понятно']")
        if cookies_message:
            logger.info("Нашли сообщение с cookies")
            try:
                cookies_message[0].click()
            except Exception:
                tb_str = traceback.format_exc()
                logger.warning(f"Не удалось принять cookies: {tb_str}")
            pause(1, 2)
        notifications_message = self.driver.find_elements(
            "xpath", "//*[@data-qa='notification-close-button']"
        )
        if notifications_message:
            logger.info("Нашли уведомление")
            try:
                notifications_message[0].click()
            except Exception:
                tb_str = traceback.format_exc()
                logger.warning(f"Не удалось закрыть уведомление: {tb_str}")

    @staticmethod
    def _define_output_file(filename: str) -> Path:
        """Определить путь к выходному файлу"""
        try:
            output_file = os.path.join(Path("data_folder/output"), filename)
            logger.info(f"Определен путь к выходному файлу: {output_file}")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка в определении расположения файла: {tb_str}")
            raise
        return output_file

    def _update_skill_stat(self, skills):
        """Обновить статистику по самым востребованным навыкам в вакансии и сохранить ее в файл"""
        for skill in skills:
            if ";" in skill:
                processed_skills = self._process_skill_string(skill)
                for skill in processed_skills:
                    self.skill_stat[skill] = self.skill_stat.get(skill, 0) + 1
            else:
                self.skill_stat[skill] = self.skill_stat.get(skill, 0) + 1
        self._save_data_to_yaml(self.skill_stat, "skill_stat.yaml")

    def _process_skill_string(self, skill_string: str) -> List[str]:
        """Разбить строку с навыками на список навыков"""
        processed_skills = []
        for part in skill_string.split(";"):
            cleaned = "".join(char for char in part if char.isalnum() or char.isspace())
            cleaned = cleaned.strip()
            if cleaned:
                processed_skills.append(cleaned)
        return processed_skills

    def _save_company(
        self,
        job: Dict[str, Any],
        apply_result: Tuple[str, str],
        vacancy: Dict[str, Any],
    ) -> None:
        """
        Определить, в какую категорию сохранять компанию и информацию о ней,
        а затем сохранить в соответствующий YAML файл
        """
        company_id = job["company_id"]
        vacancy_id = job["vacancy_id"]
        company_name = job["company_name"]
        company_job_title = job["job_title"]

        result, reason = apply_result

        if result == "Success":
            companies = self.success_companies
            filename = "success.yaml"
        elif result == "Skip":
            companies = self.skipped_companies
            filename = "skipped.yaml"
        else:
            companies = self.failed_companies
            filename = "failed.yaml"

        seen_companies = companies.get(self.resume_id, {})

        job_info = {
            "vacancy_id": vacancy_id,
            "job_title": company_job_title,
            "link": vacancy["alternate_url"],
            "reason": reason,
        }

        # Проверяем по company_id и/или по названию вакансии
        if company_id and company_id in seen_companies:
            seen_companies[company_id].append(job_info)
        elif company_name in seen_companies:
            seen_companies[company_name].append(job_info)
        else:
            if company_id:
                seen_companies[company_id] = [job_info]
            else:
                seen_companies[company_name] = [job_info]

        if result == "Success":
            self._save_company_to_yaml(filename, companies)
        else:
            self._save_company_to_yaml(filename, companies)

    def _save_company_to_yaml(self, filename: str, companies: List[Dict[str, str]]) -> None:
        """Сохранить уже просмотренные компании и их вакансии в файл"""
        output_file = self._define_output_file(filename)
        logger.info("Сохраняем данные о вакансии в YAML")
        try:
            save_yaml_file(output_file, companies)
            logger.info("Данные о компании и ее вакансии успешно сохранены в YAML файл")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(
                f"Ошибка при сохранении информации о просмотренных компаниях в YAML файл\n{tb_str}"
            )
            raise Exception(
                "Ошибка при сохранении информации о просмотренных компаниях в YAML файл"
            )

    def _load_companies_from_yaml(self, filename: str) -> List[dict]:
        """Загрузить файл c уже просмотренными компаниями и их вакансиями"""
        output_file = self._define_output_file(filename)
        logger.info(f"Загружаем компании из YAML-файла: {output_file}")
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            logger.info("Данные о компаниях и ее вакансиях успешно загружены из YAML файла")
            if self.resume_id not in data:
                data[self.resume_id] = {}
            logger.info("Информация о компаниях загружена успешно из YAML файла")
            return data
        except FileNotFoundError:
            logger.warning(f"Файл {filename} не найден, возвращаем пустой словарь")
            return {self.resume_id: {}}
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(
                f"Ошибка при загрузке информации о просмотренных компаниях в YAML файл\n{tb_str}"
            )
            return data

    def _save_data_to_yaml(self, data: Dict[str, str], filename: str) -> None:
        """Сохранить данные в файл"""
        output_file = self._define_output_file(filename)
        logger.info(f"Сохраняем данные в файл {filename}")
        try:
            save_yaml_file(output_file, data)
            logger.info(f"Данные успешно сохранены в файл {filename}")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при сохранении данных в файл {filename}\n{tb_str}")
            raise Exception(f"Ошибка при сохранении данных в файл {filename}")

    def _load_data_from_yaml(self, filename: str) -> List[dict]:
        """Загрузить файл с данными"""
        output_file = self._define_output_file(filename)
        logger.info(f"Загружаем данные из файла: {filename}")
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if filename == "answers.yaml" and not isinstance(data, list):
                    raise ValueError(f"Формат файла {filename} неверный, ожидаем список")
            logger.info(f"Данные успешно загружены из файла {filename}")
            return data
        except FileNotFoundError:
            logger.warning(f"Файл {filename} не найден, возвращаем пустой словарь")
            if filename == "answers.yaml":
                return []
            return {}
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при загрузке списка данных из файла {filename}\n{tb_str}")
            raise Exception(f"Ошибка при загрузке данных из файла {filename}")

    def _save_cover_letter(self, company_name: str, cover_letter_text: str, job_link: str) -> None:
        """Сохранить вопрос в файл"""
        output_file = self._define_output_file("cover_letters.txt")
        logger.info("Сохраняем новый сопроводительное письмо в текстовый файл")
        try:
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(80 * "=" + "\n")
                f.write(f"Компания: {company_name}\n")
                f.write(f"Ссылка: {job_link}\n")
                f.write("Сопроводительное письмо:\n\n")
                f.write(cover_letter_text + "\n\n")
            logger.info("Новое сопроводительное письмо успешно сохранено в текстовый файл")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(
                f"Ошибка при сохранении сопроводительного письма в текстовый файл. \n{tb_str}"
            )
            raise Exception("Ошибка при сохранении сопроводительного письма в текстовый файл")

    def _is_blacklisted(self, company: str) -> bool:
        """Проверить, не находится ли компания в черном списке"""
        if company in self.job_blacklist:
            logger.warning("Компания в черном списке, пропускаем")
            return True
        return False

    def _is_already_applied_to_job_or_company(self, job: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверить, откликались ли мы уже на эту вакансию"""
        company_id = job["company_id"]
        vacancy_id = job["vacancy_id"]
        company_name = job["company_name"]
        company_job_title = job["job_title"]
        my_companies = self.success_companies.get(self.resume_id, {})
        for comp in my_companies:
            if company_id == comp or self._sanitize_text(company_name) == self._sanitize_text(comp):
                if self.apply_once_at_company:
                    logger.warning(
                        "Компания уже встречалась и задана настройка не подаваться "
                        "повторно в ту же компанию, пропускаем"
                    )
                    return (
                        True,
                        "Компания уже встречалась и задана настройка не подаваться повторно в ту же компанию",
                    )
                for job_info in my_companies[comp]:
                    if vacancy_id == job_info.get("vacancy_id") or self._sanitize_text(
                        company_job_title
                    ) == self._sanitize_text(job_info["job_title"]):
                        logger.warning("Вакансия уже встречалась, пропускаем")
                        return True, "Вакансия уже встречалась"
        return False, ""

    def _sanitize_text(self, text: str) -> str:
        """Очистить текст вопроса/ответа"""
        sanitized_text = text.lower().strip().replace('"', "").replace("\\", "")
        sanitized_text = (
            re.sub(r"[\x00-\x1F\x7F]", "", sanitized_text)
            .replace("\n", " ")
            .replace("\r", "")
            .rstrip(",")
        )
        return sanitized_text

    # def write_and_upload_resume(self, job: Dict[str, Any], job_link: str):
    #     """Метод для создания резюме и сохранения его в файл"""
    #     company_name = job["company_name"].replace("/", "").strip()
    #     job_title = job["job_title"].replace("/", "").strip()
    #     logger.debug("Создаем резюме.")
    #     folder_path = f"data_folder/generated_cv/{company_name}"
    #     try:
    #         if not os.path.exists(folder_path):
    #             logger.debug(f"Создаем директорию: {folder_path}")
    #         os.makedirs(folder_path, exist_ok=True)
    #     except Exception as e:
    #         logger.error(f"Ошибка при создании директории: {folder_path}. Error: {e}")
    #         raise

    #     # сохраняем ссылку на вакансию в отдельный файл
    #     with open(folder_path + "/link.txt", "w") as f:
    #         f.write(job_link)

    #     while True:
    #         try:
    #             file_path_pdf = f"{folder_path}/CV_{company_name}_{job_title}.pdf"
    #             logger.debug(f"Создан путь для сохранения резюме: {file_path_pdf}")
    #             logger.debug(f"Создания резюме для вакансии {job_title} в {job['company_name']}")
    #             resume_pdf_base64 = self.resume_generator_manager.pdf_base64(
    #                 self.gpt_resume_generator, job
    #             )
    #             with open(file_path_pdf, "wb") as f:
    #                 f.write(base64.b64decode(resume_pdf_base64))
    #             logger.debug(f"Резюме успешно создано и сохранено по пути: {file_path_pdf}")

    #             break
    #         except HTTPStatusError as e:
    #             if e.response.status_code == 429:
    #                 retry_after = e.response.headers.get("retry-after")
    #                 retry_after_ms = e.response.headers.get("retry-after-ms")

    #                 if retry_after:
    #                     wait_time = int(retry_after)
    #                 elif retry_after_ms:
    #                     wait_time = retry_after_ms // 1000
    #                 else:
    #                     wait_time = 20
    #                 logger.warning(
    #                     f"Слишком много попыток доступа, ожидаем {wait_time} секунд перед повторной попыткой..."
    #                 )
    #                 pause(wait_time, wait_time)
    #             else:
    #                 logger.error(f"HTTP error: {e}")
    #                 raise

    #         except Exception as e:
    #             tb_str = traceback.format_exc()
    #             logger.error(
    #                 f"Неизвестная ошибка во время создания резюме на странице {self.driver.current_url}\n{tb_str}"
    #             )
    #             if "RateLimitError" in str(e):
    #                 logger.warning("Слишком много попыток доступа, пробуем повторно...")
    #                 pause(wait_time, wait_time)
    #             else:
    #                 raise

    #     file_size = os.path.getsize(file_path_pdf)
    #     max_file_size = 2 * 1024 * 1024  # 2 MB
    #     logger.debug(f"Resume file size: {file_size} bytes")
    #     if file_size > max_file_size:
    #         logger.error(f"Разме резюме больше чем {max_file_size} байт: {file_size} байт")
    #         raise ValueError("Разме резюме больше чем {max_file_size} байт.")

    #     allowed_extensions = {".pdf", ".doc", ".docx"}
    #     file_extension = os.path.splitext(file_path_pdf)[1].lower()
    #     logger.debug(f"Resume file extension: {file_extension}")
    #     if file_extension not in allowed_extensions:
    #         logger.error(f"Некорректный формат файла резюме: {file_extension}")
    #         raise ValueError(
    #             "Данный формат резюме недопустим. Только PDF, DOC, и DOCX форматы поддерживаются."
    #         )
    #     try:
    #         logger.debug(f"Загружаем резюме из пути: {file_path_pdf}")
    #         job["resume_path"] = os.path.abspath(file_path_pdf)
    #         pause(2, 3)
    #         logger.debug(f"Загрузка резюме завершена успешно: {file_path_pdf}")
    #     except Exception as e:
    #         tb_str = traceback.format_exc()
    #         logger.error(f"Неизвестная ошибка во время загрузки резюме\n{tb_str}")
    #         raise Exception(f"Резюме загружено с ошибкой")
