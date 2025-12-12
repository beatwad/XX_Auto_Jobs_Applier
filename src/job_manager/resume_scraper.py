import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import yaml
from Levenshtein import distance

from src.constants import DUMMY_PERSONAL_INFO_FEMALE, DUMMY_PERSONAL_INFO_MALE
from src.job_manager.playwright_manager import PlaywrightJobManager
from src.logger_config import logger
from src.utils.json_to_readable import transform_resume_data


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

    async def get_resume_info(self) -> Tuple[str, Dict[str, Any]]:
        """Собрать всю информацию о резюме пользователя"""
        resume_info = await self.get_selected_resume_info(self.resume_id)
        await self.raise_resume(self.resume_id, resume_info)
        self.get_personal_information(resume_info)
        self.get_work_preferences(resume_info)
        self.get_availability()
        self.get_languages(resume_info)
        # self.get_previous_job_details(resume_info)
        self.get_the_rest_resume_info(resume_info)
        self.get_education_details(resume_info)
        self.get_certificate_details(resume_info)
        self.get_recommendation_details(resume_info)
        self.get_experience_details(resume_info)
        self.get_contacts(resume_info)
        self.get_salary(resume_info)
        self.get_skills(resume_info)
        self.get_about_me(resume_info)
        # если можно начинать поиск - парсим дополнительные данные о контактах из резюме с помощью LLM
        self.parse_contacts(self.resume_info.get("about_me"))
        self.personal_information = self.resume_info["personal_information"].copy()
        self.anonymize_personal_information()
        self.save_resume_info()
        resume_readable = transform_resume_data(self.resume_info)
        resume_readable = self.anonymize_text(resume_readable)
        # del self.resume_info["personal_information"]["citizenship"] # без этого не работает GigaChat
        # del self.resume_info["legal_authorization"]
        return self.resume_info, resume_readable

    async def get_id_of_selected_resume(self) -> Tuple[str, List[str]]:
        """Получить ID нужного резюме"""
        response = await self.manager.get_my_resumes_from_browser()
        resumes = response.get("items", [])
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

    async def get_selected_resume_info(self, resume_id: str) -> Dict[str, Any]:
        """Получить информацию о нужном резюме"""
        resume_info = await self.manager.get_resume_content_from_browser(resume_id)
        return resume_info

    async def raise_resume(self, resume_id: str, resume_info: Dict[str, Any]) -> None:
        """Поднять резюме в поиске"""
        # для начала проверяем, что резюме можно поднять
        # (прошло как минимум 4 часа с последнего подъема резюме)
        logger.info("Проверяем возможность подъема резюме")
        next_publish_at = resume_info["next_publish_at"]
        next_publish_at = datetime.fromisoformat(next_publish_at).replace(tzinfo=None)
        dt_now = datetime.now()
        # если поднять можно - поднимаем # TODO: replace with button click
        # if dt_now >= next_publish_at:
        #     url = f"https://api.hh.ru/resumes/{resume_id}/publish"
        #     await self.manager.api_request(url, method="POST")
        #     logger.info("Резюме успешно поднято")

    def get_personal_information(self, resume_info: dict[str, Any]) -> None:
        # ... (rest of methods remain synchronous as they process data)
        # Just copy-paste the rest from original file
        """Собрать персональную информацию"""
        self.resume_info["personal_information"] = {}
        # собрать информацию о ФИО
        self.resume_info["personal_information"]["first_name"] = resume_info["first_name"]
        self.resume_info["personal_information"]["last_name"] = resume_info["last_name"]
        self.resume_info["personal_information"]["middle_name"] = resume_info["middle_name"]
        # собрать информацию о месте проживания
        self.resume_info["personal_information"]["current_city"] = resume_info["area"]["name"]
        if resume_info["metro"]:
            self.resume_info["personal_information"]["metro"] = resume_info["metro"]["name"]
        else:
            self.resume_info["personal_information"]["metro"] = ""
        self._get_vehicle(resume_info)
        # собрать информацию о дне рождения
        if resume_info["birth_date"]:
            # self.resume_info["personal_information"]["birthday"] = resume_info["birth_date"]
            self.resume_info["personal_information"]["age"] = resume_info["age"]
        else:
            # self.resume_info["personal_information"]["birthday"] = ""
            self.resume_info["personal_information"]["age"] = ""
        # собрать остальные личные данные (пол, гражданство, разрешение на работу)
        self.resume_info["personal_information"]["sex"] = resume_info["gender"]["name"]
        if len(resume_info["citizenship"]) > 0:
            self.resume_info["personal_information"]["citizenship"] = []
            for citizenship in resume_info["citizenship"]:
                self.resume_info["personal_information"]["citizenship"].append(citizenship["name"])
        else:
            self.resume_info["personal_information"]["citizenship"] = "Россия"
        if len(resume_info["work_ticket"]) > 0:
            self.resume_info["personal_information"]["legal_authorization"] = []
            for work_ticket in resume_info["work_ticket"]:
                self.resume_info["personal_information"]["legal_authorization"].append(
                    work_ticket["name"]
                )
        else:
            self.resume_info["personal_information"]["legal_authorization"] = "Россия"

    def _get_vehicle(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о правах и личном траспорте"""
        if resume_info["has_vehicle"]:
            self.resume_info["personal_information"]["has_vehicle"] = resume_info["has_vehicle"]
        else:
            self.resume_info["personal_information"]["has_vehicle"] = False
        if resume_info["driver_license_types"]:
            self.resume_info["personal_information"]["driver_license_types"] = [
                ri["id"] for ri in resume_info["driver_license_types"]
            ]

    def get_work_preferences(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о предпочтениях по работе"""
        self.resume_info["work_preferences"] = {}
        self.resume_info["work_preferences"]["position"] = self.job_title
        self.resume_info["work_preferences"]["can_relocate"] = resume_info["relocation"]["type"][
            "name"
        ]

    def get_availability(self) -> None:
        """Собрать информацию о том как скоро готов выйти на работу"""
        self.resume_info["availability"] = {}
        self.resume_info["availability"]["notice_period"] = "2 недели"

    def get_languages(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о языках"""
        self.resume_info["languages"] = {}
        for language in resume_info["language"]:
            name = language["name"]
            level = language["level"]["name"]
            self.resume_info["languages"][name] = level

    def get_previous_job_details(self, resume_info: dict[str, Any]) -> None:
        """Добавить информацию о предыдущей работе"""
        if not resume_info["experience"]:
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

    def get_the_rest_resume_info(self, resume_info: dict[str, Any]) -> None:
        """Получить оставшуюся информацию непосредственно из резюме"""
        self.get_more_work_preferences(resume_info)

    def get_more_work_preferences(self, resume_info: dict[str, Any]) -> None:
        """Собрать доп информацию о предпочтениях по работе"""
        self._get_professional_roles(resume_info)
        self._get_job_type(resume_info)

    def _get_professional_roles(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о специализациях"""
        if len(resume_info["professional_roles"]) > 0:
            role_list = []
            for role in resume_info["professional_roles"]:
                role_list.append(role["name"])
            self.resume_info["work_preferences"]["professional_roles"] = role_list

    def _get_job_type(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о предпочитаемом виде занятости и графике работы"""
        if len(resume_info["employments"]) > 0:
            employment_list = []
            for employment in resume_info["employments"]:
                employment_list.append(employment["name"])
            self.resume_info["work_preferences"]["employments"] = employment_list
        else:
            self.resume_info["work_preferences"]["employments"] = ""
        if len(resume_info["schedules"]) > 0:
            schedule_list = []
            for schedule in resume_info["schedules"]:
                schedule_list.append(schedule["name"])
            self.resume_info["work_preferences"]["schedules"] = schedule_list
        else:
            self.resume_info["work_preferences"]["schedules"] = ""
        self.resume_info["work_preferences"]["travel_time_to_work"] = resume_info["travel_time"][
            "name"
        ]
        self.resume_info["work_preferences"]["ready_to_business_trips"] = resume_info[
            "business_trip_readiness"
        ]["name"]

    def get_education_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию об образовании пользователя"""
        try:
            self.resume_info["education_details"] = {
                "level": resume_info["education"]["level"]["name"]
            }
        except TypeError:
            self.resume_info["education_details"] = {}
        self._get_primary_education_details(resume_info)
        self._get_elementary_education_details(resume_info)
        self._get_additional_education_details(resume_info)
        self._get_attestation_details(resume_info)

    def _get_primary_education_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию об основном образовании пользователя"""
        if len(resume_info["education"]["primary"]) > 0:
            education_list = []
            for ed in resume_info["education"]["primary"]:
                education_dict = {}
                for key, value in ed.items():
                    if "id" not in key and value is not None:
                        if key == "education_level":
                            education_dict[key] = value["name"]
                        else:
                            education_dict[key] = value
                education_list.append(education_dict)
            self.resume_info["education_details"]["primary"] = education_list

    def _get_elementary_education_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о базовом образовании пользователя"""
        if len(resume_info["education"]["elementary"]) > 0:
            education_list = []
            for ed in resume_info["education"]["elementary"]:
                education_dict = {}
                for key, value in ed.items():
                    if "id" not in key and value is not None:
                        education_dict[key] = value
                education_list.append(education_dict)
            self.resume_info["education_details"]["elementary"] = education_list

    def _get_additional_education_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о курсах и повышении квалификации пользователя"""
        if len(resume_info["education"]["additional"]) > 0:
            education_list = []
            for ed in resume_info["education"]["additional"]:
                education_dict = {}
                for key, value in ed.items():
                    if "id" not in key and value is not None:
                        education_dict[key] = value
                education_list.append(education_dict)
            self.resume_info["education_details"]["additional"] = education_list

    def _get_attestation_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о тестах, экзаменах и аттестатах пользователя"""
        if len(resume_info["education"]["attestation"]) > 0:
            education_list = []
            for ed in resume_info["education"]["attestation"]:
                education_dict = {}
                for key, value in ed.items():
                    if "id" not in key and value is not None:
                        education_dict[key] = value
                education_list.append(education_dict)
            self.resume_info["education_details"]["attestation"] = education_list

    def get_experience_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о рабочем опыте пользователя"""
        self.resume_info["experience_details"] = {}
        if resume_info["total_experience"]:
            years = int(resume_info["total_experience"]["months"]) // 12
            years = max(years, 1)
            self.resume_info["experience_details"]["total_experience_years"] = years
        if len(resume_info["experience"]) > 0:
            experience_list = []
            for exp in resume_info["experience"]:
                experience_dict = {}
                for key, value in exp.items():
                    if "id" not in key and value is not None:
                        if key == "industries":
                            experience_dict[key] = [v["name"] for v in value]
                        elif key in ["area", "employer"]:
                            experience_dict[key] = value["name"]
                        elif key in ["start", "end"]:
                            experience_dict[key + "_date"] = value
                        else:
                            experience_dict[key] = value
                experience_list.append(experience_dict)
            self.resume_info["experience_details"]["details"] = experience_list

    def save_resume_info(self) -> None:
        """Сохранить резюме в файл"""
        with open("data_folder/output/resume.yaml", "w", encoding="utf-8") as f:
            yaml.dump(self.resume_info, f, allow_unicode=True, default_flow_style=False)

    def get_contacts(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о контактах пользователя"""
        # собираем основную информацию о контактах
        for site in resume_info["site"]:
            if "t.me" in site["url"]:
                self.resume_info["personal_information"]["telegram"] = site["url"]
            elif "wa.me" in site["url"]:
                self.resume_info["personal_information"]["whatsapp"] = site["url"]
            elif site["type"]["id"] == "linkedin":
                self.resume_info["personal_information"]["linkedin"] = site["url"]
            elif site["type"]["id"] == "skype":
                self.resume_info["personal_information"]["skype"] = site["url"]
            elif site["type"]["id"] == "moi_krug":
                self.resume_info["personal_information"]["moi_krug"] = site["url"]
            elif site["type"]["id"] == "livejournal":
                self.resume_info["personal_information"]["livejournal"] = site["url"]
            else:
                self.resume_info["personal_information"]["other_site"] = site["url"]
        for contact in resume_info["contact"]:
            if contact["type"]["id"] == "cell":  # получить телефон
                self.resume_info["personal_information"]["phone"] = contact["value"]["formatted"]
                if contact["preferred"] is True:
                    self.resume_info["personal_information"]["preferred_contact"] = "phone"
            elif contact["type"]["id"] == "email":  # получить email
                self.resume_info["personal_information"]["email"] = contact["value"]
                if contact["preferred"] is True:
                    self.resume_info["personal_information"]["preferred_contact"] = "email"

    def parse_contacts(self, resume_info: dict[str, Any]) -> None:
        """Собрать дополнительную информацию о контактах из описания резюме"""
        if resume_info:
            output = self.gpt_answerer_component.parse_contacts(resume_info)
            for key, value in output.items():
                key_, value_ = key.lower(), value.lower()
                if key_ not in self.resume_info["personal_information"] and value_ != "no info":
                    self.resume_info["personal_information"][key_] = value

    def get_salary(self, resume_info: dict[str, Any]) -> None:
        if resume_info["salary"]:
            self.resume_info["salary_expectations"] = resume_info["salary"].copy()
        else:
            resume_info["salary"] = ""

    def get_skills(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию об навыках пользователя"""
        if resume_info["skill_set"]:
            self.resume_info["skills"] = resume_info["skill_set"].copy()
        else:
            self.resume_info["skills"] = ""

    def get_about_me(self, resume_info: dict[str, Any]) -> None:
        """Собрать общую информацию о пользователе"""
        if resume_info["skills"]:
            self.resume_info["about_me"] = resume_info["skills"]
        else:
            self.resume_info["about_me"] = ""

    def get_certificate_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о сертификатах пользователя"""
        if len(resume_info["certificate"]) > 0:
            certificate_list = []
            for cert in resume_info["certificate"]:
                certificate_dict = {}
                for key, value in cert.items():
                    if value is not None:
                        certificate_dict[key] = value
                certificate_list.append(certificate_dict)
            self.resume_info["certifications"] = certificate_list

    def get_recommendation_details(self, resume_info: dict[str, Any]) -> None:
        """Собрать информацию о сертификатах пользователя"""
        if len(resume_info["recommendation"]) > 0:
            recommendation_list = []
            for cert in resume_info["recommendation"]:
                recommendation_dict = {}
                for key, value in cert.items():
                    if value is not None:
                        recommendation_dict[key] = value
                recommendation_list.append(recommendation_dict)
            self.resume_info["recommendation"] = recommendation_list

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
            elif key in ["last_name_2"]:
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
                # LLM периодически галлюцинирует и выдает неправильную фамилию
                # этот код добавлен с целью исправления данного бага
                if key in ["last_name_2"]:
                    key_ = "last_name"
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
