import re
from typing import Any, Dict, List, Tuple

import yaml
from Levenshtein import distance

from src.constants import DUMMY_PERSONAL_INFO_FEMALE, DUMMY_PERSONAL_INFO_MALE
from src.job_manager.playwright_manager import PlaywrightJobManager
from src.logger_config import logger
from src.utils.utils import load_app_config
from src.utils.json_to_readable import transform_resume_data

config = load_app_config()
ANONYMIZE = config.get("ANONYMIZE", True)


class ResumeScraper:
    def __init__(
        self,
        manager: PlaywrightJobManager,
        job_title: str,
        resume_id: str,
        gpt_answerer_component: Any,
    ):
        self.manager = manager
        self.job_title = job_title
        self.resume_info = {}
        self.resume_id = resume_id
        self.personal_information = {}
        self.resume_info["general_knowledge_questions"] = ""
        self.github_links = []
        self.gpt_answerer_component = gpt_answerer_component

    async def get_resume_parameters(self) -> Tuple[str, List[str]]:
        """Получить ID нужного резюме"""
        return await self.get_id_of_selected_resume()

    async def get_id_of_selected_resume(self) -> Tuple[str, List[str]]:
        """Получить ID нужного резюме"""
        response = await self.manager.get_my_resumes_from_browser()
        resumes = response.get("items", [])
        if not resumes:
            raise ValueError("Список резюме пуст: не удалось получить резюме из профиля hh.ru")
        # найти среди резюме наиболее схожее по названию с должностью, что указана в настройках
        resume_titles = [r["title"] if r["title"] else "" for r in resumes]
        # если не задана должность - возвращаем первое резюме
        if not self.job_title:
            # если в параметрах поиска есть resume_id - используем резюме с этим id
            if self.resume_id:
                for i, resume in enumerate(resumes):
                    if resume["id"] == self.resume_id:
                        self.job_title = resume_titles[i]
                        return resume["id"], resume_titles
            self.resume_id = resumes[0]["id"]
            self.job_title = resume_titles[0]
            return resumes[0]["id"], resume_titles
        distances = [
            (i, distance(self.job_title.lower(), title.lower()))
            for i, title in enumerate(resume_titles)
        ]
        best_titile_idx = min(distances, key=lambda x: x[1])[0]
        best_match_resume = resumes[best_titile_idx]
        best_match_resume_title = resume_titles[best_titile_idx]
        resume_id = best_match_resume["id"]
        logger.info(
            f"Найден наиболее подходящий вариант резюме для должности {self.job_title}: {best_match_resume_title}"
        )
        self.job_title = best_match_resume_title
        self.resume_id = resume_id
        return resume_id, resume_titles

    async def get_resume_info(self) -> Tuple[str, Dict[str, Any]]:
        """Собрать всю информацию о резюме пользователя"""
        self.resume_info = await self.get_selected_resume_info(self.resume_id)
        self.get_previous_job_details()
        # если можно начинать поиск - парсим дополнительные данные о контактах из резюме с помощью LLM
        personal_information = self.resume_info["personal_information"]
        for key in ["telegram", "whatsapp", "phone", "email", "linkedin"]:
            if not personal_information.get(key):
                self.parse_contacts(self.resume_info.get("about_me"))
                break
        self.personal_information = self.resume_info["personal_information"].copy()
        self.anonymize_personal_information()
        self.save_resume_info()
        resume_readable = transform_resume_data(self.resume_info)
        resume_readable = self.anonymize_text(resume_readable)
        return self.resume_info, resume_readable

    async def get_selected_resume_info(self, resume_id: str) -> Dict[str, Any]:
        """Получить информацию о нужном резюме"""
        resume_info = await self.manager.get_resume_content_from_browser(resume_id)
        return resume_info

    def get_previous_job_details(self) -> None:
        """Добавить информацию о предыдущей работе"""
        if not self.resume_info["experience"]:
            return
        self.resume_info["previous_job_details"] = {}
        self.resume_info["previous_job_details"]["why_leave_previous_job"] = (
            "На предыдущей работе не устраивало отсутствие карьерного роста и интересных задач."
        )
        self.resume_info["previous_job_details"]["team"] = (
            "Коллектив на предыдущей работе был дружный, не токсичный."
        )
        self.resume_info["previous_job_details"]["boss"] = (
            "Отношения с начальством были хорошие, токсичного поведения замечено не было."
        )

    def parse_contacts(self, resume_info: str) -> None:
        """Парсим контакты из резюме"""
        logger.info("Парсим контакты из резюме")
        contacts = self.gpt_answerer_component.parse_contacts(resume_info)
        if contacts.get("Phone"):
            self.resume_info["personal_information"]["phone"] = contacts.get("Phone")
        if contacts.get("Email"):
            self.resume_info["personal_information"]["email"] = contacts.get("Email")
        if contacts.get("LinkedIn"):
            self.resume_info["personal_information"]["linkedin"] = contacts.get("LinkedIn")
        if contacts.get("Telegram"):
            self.resume_info["personal_information"]["telegram"] = contacts.get("Telegram")
        if contacts.get("Whatsapp"):
            self.resume_info["personal_information"]["whatsapp"] = contacts.get("Whatsapp")

    def save_resume_info(self) -> None:
        """Сохранить резюме в файл"""
        with open("data_folder/output/resume.yaml", "w", encoding="utf-8") as f:
            yaml.dump(self.resume_info, f, allow_unicode=True, default_flow_style=False)

    def anonymize_personal_information(self) -> None:
        """Анонимазовать персональные данные путем подмены их на данные-пустышки"""
        sex = self.personal_information.get("sex")
        if sex.lower() == "женский":
            dummy_pesonal_info = DUMMY_PERSONAL_INFO_FEMALE
        else:
            dummy_pesonal_info = DUMMY_PERSONAL_INFO_MALE
        # анонимизировать графы "персональная информация" и "обо мне"
        for key, value in dummy_pesonal_info.items():
            if self.resume_info["personal_information"].get(key):
                self.resume_info["personal_information"][key] = value

    def anonymize_text(self, input_: str) -> str:
        """If some key words are found in resume text - anonymize them"""
        if not ANONYMIZE:
            return input_
        sex = self.resume_info["personal_information"].get("sex")
        if sex.lower() == "женский":
            dummy_pesonal_info = DUMMY_PERSONAL_INFO_FEMALE
        else:
            dummy_pesonal_info = DUMMY_PERSONAL_INFO_MALE
        for key, value in dummy_pesonal_info.items():
            # анонимизируем имя пользователя в ссылке на github
            if key == "github":
                self.github_links = re.findall(r"https?://(?:www\.)?github\.com/([^\s/]+)", input_)
                self.github_links = [
                    f"https://github.com/{github_link}" for github_link in self.github_links
                ]
                if self.github_links:
                    input_ = re.sub(
                        r"https?://(?:www\.)?github\.com/([^\s/]+)",
                        value,
                        input_,
                    )
            elif key in ["first_name_2", "first_name_3", "last_name_2", "telegram_2", "telegram_3"]:
                continue
            else:
                if not self.resume_info["personal_information"].get(key):
                    continue
                value_to_replace = self.personal_information[key]
                if "github" in value_to_replace:
                    continue
                value_to_replace_escaped = re.escape(value_to_replace)
                if key in ["phone"]:
                    input_ = re.sub(rf"{value_to_replace_escaped}", value, input_)
                else:
                    input_ = re.sub(rf"\b{value_to_replace_escaped}\b", value, input_)
        return input_

    def deanonymize_personal_information(self, output: str) -> str:
        """Деанонимазовать данные в ответе"""
        if not ANONYMIZE:
            return output
        sex = self.personal_information.get("sex")
        if sex.lower() == "женский":
            dummy_pesonal_info = DUMMY_PERSONAL_INFO_FEMALE
        else:
            dummy_pesonal_info = DUMMY_PERSONAL_INFO_MALE
        for key, value_to_replace in dummy_pesonal_info.items():
            if key == "github":
                for i, github_link in enumerate(self.github_links):
                    output = re.sub(
                        r"https?://(?:www\.)?github\.com/([^\s/]+)",
                        github_link,
                        output,
                        count=i + 1,
                    )
            else:
                if "github" in value_to_replace:
                    continue
                # LLM периодически галлюцинирует и выдает неправильное имя или фамилию или telegram
                # этот код добавлен с целью исправления данного бага
                if key in ["first_name_2", "first_name_3"]:
                    key_ = "first_name"
                elif key in ["last_name_2"]:
                    key_ = "last_name"
                elif key in ["telegram_2", "telegram_3"]:
                    key_ = "telegram"
                else:
                    key_ = key
                if not self.personal_information.get(key_):
                    continue
                value = self.personal_information[key_]
                value_to_replace_escaped = re.escape(value_to_replace)
                if key_ in ["phone"]:
                    output = re.sub(rf"{value_to_replace_escaped}", value, output)
                else:
                    output = re.sub(rf"\b{value_to_replace_escaped}\b", value, output)
        return output
