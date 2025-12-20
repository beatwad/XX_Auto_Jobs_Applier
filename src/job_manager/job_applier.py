import os
import re
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from src.app_config import (
    COVER_LETTER_MODE,
    MINIMUM_WAIT_TIME_SEC,
    MONKEY_MODE,
    RESUME_MODE,
    SKILL_STAT_MODE,
)
from src.constants import LAST_RUN_FILE, SEARCH_CONFIG_FILE
from src.job_manager.playwright_manager import PlaywrightJobManager
from src.logger_config import logger
from src.telegram.telegram_manager import TelegramReportSender
from src.utils.utils import (
    load_yaml_file,
    pause,
    save_yaml_file,
    sleep,
)

search_config = load_yaml_file(SEARCH_CONFIG_FILE)
FIXED_COVER_LETTER = search_config.get("cover_letter")
MAX_APPLIES_NUM = 100


class JobApplier:
    """Класс для поиска и рассылки откликов работодателям"""

    def __init__(self, manager: PlaywrightJobManager, resume_component: Any, search_component: Any):
        logger.info("Инициализация JobApplier")
        self.manager = manager
        self.resume_component = resume_component
        self.search_component = search_component
        self.gpt_answerer = None
        self.jobs_no_info = []  # вакансии, на которые не откликнулись из-за отсутствия информации
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

    async def get_vacancies_from_page(self, page_num: int = 0) -> List[Any]:
        """Получить вакансии с очередной страницы"""
        return await self.manager.get_vacancies_from_page(page_num)

    async def scrape_vacancy(self, vacancy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Собрать всю информацию о работодателе
        для дальнейшей передачи в LLM
        """
        job = {}
        job["job_title"] = vacancy["name"]
        job["vacancy_id"] = vacancy["id"]

        # Safe access to optional fields
        if "employer" in vacancy and vacancy["employer"]:
            job["company_id"] = vacancy["employer"].get("id")
            job["company_name"] = vacancy["employer"]["name"]
            job["accredited_it_employer"] = vacancy["employer"].get("accredited_it_employer", False)
        else:
            job["company_id"] = None
            job["company_name"] = "Unknown"
            job["accredited_it_employer"] = False

        # Fetch full details via Playwright
        try:
            full_info = await self.manager.get_vacancy_full_info(vacancy["alternate_url"])
            job["job_description"] = re.sub(r"<[^>]+>", "", full_info.get("description", ""))
            job["has_test_task"] = False  # Simplified for now, scraping this is harder
        except Exception as e:
            logger.error(f"Failed to scrape vacancy details: {e}")
            job["job_description"] = ""

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

    async def start_applying(self) -> None:
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
        # запускаем поиск вакансий
        await self.search_component.start_search()
        # продолжаем пока не достигнем максимально допустимого числа откликов
        while self.success_applies_num < self.max_applies_num and self.applies_num < 400:
            # идем по всем страницам пока они не закончатся
            vacancies = await self.get_vacancies_from_page(self.page_num)
            if len(vacancies) == 0:
                if self.page_num == 0:
                    logger.warning("По данному поисковому запросу не найдено ни одной вакансии")
                break
            for vacancy in vacancies:
                url = vacancy.get("alternate_url")
                try:
                    result = await self.send_repsonse(vacancy)
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

    async def send_repsonse(self, vacancy: Dict[str, Any]) -> str:
        """Разослать отклики всем работодателям на странице"""
        # собрать описание вакансии
        job = await self.scrape_vacancy(vacancy)
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
        elif (not self.hh_login or not self.hh_password) and job.get("has_test_task"):
            # For now assume has_test_task is checked in apply flow or ignored
            pass

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
                # self._update_skill_stat(self.job_key_skills) # TODO: re-enable scraping skills
                apply_result = await self.apply_job(vacancy, company_name, company_job_title, job)
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

    async def apply_job(
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
                return "Skip", "COVER_LETTER_MODE"
            elif SKILL_STAT_MODE is True:
                # если находимся в режиме сбора статистики по навыкам - не откликаемся на вакансии,
                # только сохраняем статистику по навыкам в файл
                logger.info(
                    "Находимся в режиме сбора статистики по навыкам - не откликаемся на вакансии"
                )
                return "Skip", "SKILL_STAT_MODE"
            elif RESUME_MODE is True:
                # если находимся в режиме резюме - не откликаемся на вакансии,
                # только сохраняем сгенерированные резюме
                logger.info("Находимся в режиме резюме - не откликаемся на вакансии")
                # self.write_and_upload_resume(job, vacancy["alternate_url"]) # Disabled in migration for simplicity
                return "Skip", "RESUME_MODE"
            else:
                return await self.manager.apply_to_vacancy(
                    vacancy["alternate_url"],
                    cover_letter_text,
                    self.gpt_answerer,
                    self.resume_titles,
                )
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(
                f"Неизвестная ошибка на странице {vacancy.get('alternate_url')} во время отклика на вакансию {job_title} компании {company_name}\n{tb_str}"
            )
            return "Error", str(e)

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
