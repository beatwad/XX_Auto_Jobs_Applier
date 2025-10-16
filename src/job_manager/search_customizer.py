from typing import Any, Dict, List, Union

from Levenshtein import distance

from src.logger_config import logger


class SearchCustomizer:
    def __init__(self, api):
        self.api = api
        self.resume = None
        self.search_params = {}

    def set_resume(self, resume_id: str, resume: Dict[str, Any]) -> None:
        """Добавляем резюме для анализа."""
        self.resume_id = resume_id
        self.resume = resume

    def set_advanced_search_params(self, parameters: Dict[str, Any]) -> None:
        """Установка параметрок поиска"""
        logger.info("Установка параметров SearchCustomizer")
        # загрузка необязательных параметров
        self.search_params["text"] = parameters.get("keywords") or ""
        self.search_params["search_field"] = self._get_search_field_ids(parameters)
        self.search_params["experience"] = self._get_experience_id(parameters)
        self.search_params["employment"] = self._get_employment_ids(parameters)
        self.search_params["schedule"] = self._get_schedule_ids(parameters)
        self.search_params["area"] = self._get_area_ids(parameters)
        self.search_params["metro"] = self._get_metro_ids(parameters)
        self.search_params["professional_role"] = self._get_professional_role_id(parameters)
        self.search_params["industry"] = self._get_industry_ids(parameters)
        self.search_params["salary"] = parameters.get("salary") or 0
        self.search_params["currency"] = self._get_currency_id(parameters)
        self.search_params["label"] = self._get_vacancy_label_ids(parameters)
        self.search_params["only_with_salary"] = parameters.get("only_with_salary") or False
        self.search_params["period"] = self._get_period(parameters)
        self.search_params["order_by"] = self._get_order_by_id(parameters)
        self.search_params["part_time"] = self._get_part_time_ids(parameters)
        logger.info("Параметры SearchCustomizer успешно установлены")
        # настройки поиска, которые есть в интерфейсе hh.ru, но отсутствуют в API
        self.words_to_exclude = ""
        self.districts = ""
        self.education = ""

    def _get_search_field_ids(self, parameters: Dict[str, Any]) -> List[str]:
        """Получить id настроек области поиска"""
        search_field = parameters.get("search_field") or {}
        search_field_ids = []
        for key, value in search_field.items():
            if value is True:
                search_field_ids.append(key)
        return search_field_ids

    def _get_experience_id(self, parameters: Dict[str, Any]) -> Union[str, List[str]]:
        """Получить id настройки опыта"""
        experience = parameters.get("experience") or {}
        experience_ids = []
        for key, value in experience.items():
            if value is True:
                if key == "doesntMatter":
                    return ""
                experience_ids.append(key)
        if not experience_ids:
            return ""
        return experience_ids

    def _get_employment_ids(self, parameters: Dict[str, Any]) -> List[str]:
        """Получить id настроек занятосли"""
        employment = parameters.get("employment") or {}
        employment_ids = []
        for key, value in employment.items():
            if value is True:
                employment_ids.append(key)
        return employment_ids

    def _get_schedule_ids(self, parameters: Dict[str, Any]) -> None:
        """Получить id настроек графика работы"""
        schedule = parameters.get("schedule") or {}
        schedule_ids = []
        for key, value in schedule.items():
            if value is True:
                schedule_ids.append(key)
        return schedule_ids

    def _get_area_ids(self, parameters: Dict[str, Any]) -> List[str]:
        """Получаем id регионов"""
        regions = parameters.get("area") or ""
        if not regions:
            return []
        regions = regions.split(";")
        regions = [region.lower().strip() for region in regions]
        region_ids = []
        # получаем список стран, в которых надо искать нужный нам регион
        if len(self.resume["personal_information"]["citizenship"]) > 0:
            countries = self.resume["personal_information"]["citizenship"]
            countries = [country.lower() for country in countries]
        elif len(self.resume["personal_information"]["legal_authorization"]) > 0:
            countries = self.resume["personal_information"]["legal_authorization"]
            countries = [country.lower() for country in countries]
        else:
            countries = ["россия"]

        areas = self.api.api_request("https://api.hh.ru/areas")

        # Проходим по всем странам и городам и берем первый совпавший регион или город
        for region in regions:
            region_id = None
            for country_data in areas:
                if country_data["name"].lower() in countries:
                    for region_data in country_data.get("areas", []):
                        if region_data["name"].lower() == region:
                            region_id = region_data["id"]
                            region_ids.append(region_id)
                            break
                        for city_data in region_data.get("areas", []):
                            if city_data["name"].lower() == region:
                                region_id = city_data["id"]
                                region_ids.append(region_id)
                                break
                        if region_id:  # Если нашли город или регион, выходим из цикла
                            break
                if region_id:
                    break
        return region_ids

    def _get_metro_ids(self, parameters: Dict[str, Any]) -> List[str]:
        """Получаем id станций метро"""
        metro = parameters.get("metro") or ""
        if not metro:
            return []
        metro = metro.split(",")
        metro = [station.lower().strip() for station in metro]
        metro_ids = []

        cities = self.api.api_request("https://api.hh.ru/metro")

        # Проходим по всем странам и городам и берем первый совпавший регион или город
        for metro_station in metro:
            metro_id = None
            for city in cities:
                if city["id"] in self.search_params["area"]:
                    for line in city["lines"]:
                        for station in line["stations"]:
                            if station["name"].lower() == metro_station:
                                metro_id = station["id"]
                                metro_ids.append(metro_id)
                                break
                    if metro_id:
                        break
                if metro_id:
                    break
        return metro_ids

    def _get_professional_role_id(self, parameters: Dict[str, Any]) -> str:
        """Получаем id профессиональной области"""
        professional_role = parameters.get("professional_role") or ""
        if not professional_role:
            return ""
        professional_role = professional_role.lower()
        distances = []

        categories = self.api.api_request("https://api.hh.ru/professional_roles")

        for category in categories["categories"]:
            for role in category["roles"]:
                id = role["id"]
                names = role["name"].lower().strip()
                for name in names.split(","):
                    distances.append((id, name, distance(professional_role, name)))

        professional_role_id = min(distances, key=lambda x: x[-1])[0]
        return professional_role_id

    def _get_industry_ids(self, parameters: Dict[str, Any]) -> List[str]:
        """Получаем id индустрии"""
        industries = parameters.get("industry") or ""
        if not industries:
            return []

        industries = industries.split(",")
        industries = [industry.lower().strip() for industry in industries]
        industry_ids = []

        categories = self.api.api_request("https://api.hh.ru/industries")

        for industry in industries:
            for category in categories:
                for industry_ in category["industries"]:
                    if industry_["name"].lower() == industry:
                        industry_ids.append(industry_["id"])

        return industry_ids

    def _get_currency_id(self, parameters: Dict[str, Any]) -> str:
        "Получаем id валюты"
        currency = parameters.get("currency") or {}
        for key, value in currency.items():
            if value is True:
                return key
        return ""

    def _get_vacancy_label_ids(self, parameters: Dict[str, Any]) -> List[str]:
        """Получить id настроек меток вакансий"""
        vacancy_labels = parameters.get("vacancy_label") or {}
        vacancy_label_ids = []
        for key, value in vacancy_labels.items():
            if value is True:
                vacancy_label_ids.append(key)
        return vacancy_label_ids

    def _get_period(self, parameters: Dict[str, Any]) -> int:
        """Получить значение количества дней, в пределах которых производится поиск по вакансиям"""
        period = parameters.get("period") or {}
        for key, value in period.items():
            if key == "all_time" and value is True:
                return 0
            if key == "month" and value is True:
                return 30
            if key == "week" and value is True:
                return 7
            if key == "three_days" and value is True:
                return 3
            if key == "one_day" and value is True:
                return 1
        return 0

    def _get_order_by_id(self, parameters: Dict[str, Any]) -> str:
        """Получить id сортировки списка вакансий"""
        order_by = parameters.get("order_by") or {}
        for key, value in order_by.items():
            if value is True:
                return key

    def _get_part_time_ids(self, parameters: Dict[str, Any]) -> List[str]:
        """Получить id настроек вакансий для подработки"""
        part_time = parameters.get("part_time") or {}
        part_timel_ids = []
        for key, value in part_time.items():
            if value is True:
                part_timel_ids.append(key)
        return part_timel_ids
