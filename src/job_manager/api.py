from typing import Any, Dict, Union

import requests

from src.constants import SECRETS_FILE
from src.logger_config import logger
from src.utils.utils import load_yaml_file, pause, save_yaml_file


class HeadHunterAPI:
    """Класс для входа и получения данных для входа на сайт"""

    def __init__(self, secrets: Dict[str, Any]):
        logger.info("Установка параметров HeadHunterAPI")
        self.secrets = secrets
        self.access_token = secrets["access_token"]
        self.refresh_token = secrets["refresh_token"]
        self.secrets_file = SECRETS_FILE
        if not self.secrets.get("user_id", ""):
            logger.info("Не смогли найти ID пользователя в настройках поиска")
            self._get_user_id()

    def api_request(
        self, url: str, type_: str = "get", params: Dict[str, str] = {}
    ) -> Dict[str, str]:
        response = self._send_request(url, type_, params)
        if "error" in response:
            raise ValueError(
                f"Неизвестная ошибка во время доступа к API HH: {response['error_description']}"
            )

        if "errors" in response:
            for error in response["errors"]:
                # если наткнулись на лимит - делаем паузу
                if error.get("type") == "too_many_requests":
                    logger.warning("Слишком много запросов, ждем 1-2 часа")
                    pause(3600, 7200)
                    # далее повторяем запрос еще раз
                    response = self._send_request(url, type_, params)
                    break
                # если увидели сообщение о том, что истек срок токена, пытаемся обновить его
                if error.get("value") == "token_expired":
                    logger.warning("Время жизни токена истекло")
                    self.refress_access_token()
                    # далее повторяем запрос еще раз
                    response = self._send_request(url, type_, params)
                    break
                elif (
                    error.get("value") == "test_required"
                    or error.get("value") == "limit_exceeded"
                    or error.get("value") == "application_denied"
                    or error.get("value") == "already_applied"
                ):
                    # если требуется ответить на вопросы или лимит откликов исчерпан или вакансия уже неактивна - пропускаем
                    break
            else:
                raise ValueError(
                    f"Неизвестная ошибка во время доступа к API HH: {response['errors']}"
                )
        return response

    def refress_access_token(self) -> None:
        """Обновление токена доступа к hh API"""
        logger.info("Пытаемся обновить токен доступа")
        url = "https://api.hh.ru/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        response = requests.post(url, data=data)
        tokens = response.json()

        if "access_token" in tokens and "refresh_token" in tokens:
            logger.info("Токен доступа обновлен")
            self.secrets["access_token"] = tokens["access_token"]
            self.secrets["refresh_token"] = tokens["refresh_token"]
            self.access_token = self.secrets["access_token"]
            self.refresh_token = self.secrets["refresh_token"]
            logger.info("Записываем обновленные токены доступа в файл secrets.yaml")
            self._update_secretes()
            return

        if "error" in tokens:
            raise ValueError(f"Ошибка во время обновления токена: {tokens['error']}")

        if "errors" in tokens:
            raise ValueError(f"Ошибки во время обновления токена: {tokens['errors']}")

        if "error_description" in tokens:
            if tokens["error_description"] != "token not expired":
                raise ValueError(f"Ошибка во время обновления токена: {tokens}")
            logger.info("Обновление токена доступа не требуется")

        raise ValueError(f"Неизвестная ошибка во время обновления токена: {tokens}")

    def _send_request(
        self, url: str, type_: str = "get", params: Union[Dict[str, str], None] = None
    ) -> Dict[str, str]:
        """Непосредственно отправка запроса"""
        if params is None:
            params = {}
        headers = {"Authorization": f"Bearer {self.access_token}"}
        if type_ == "get":
            response = requests.get(url, headers=headers, params=params)
        elif type_ == "post":
            response = requests.post(url, headers=headers, params=params)
        else:
            raise ValueError("type_ parameter can only be 'post' or 'get'")
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return {"response_text": response.text}

    def _get_user_id(self) -> str:
        """Получение ID пользователя на hh.ru"""
        url = "https://api.hh.ru/me"
        response = self.api_request(url, type_="get")
        self.secrets["user_id"] = response["id"]
        logger.info("Получили ID пользователя на сайте hh.ru, обновляем файл настроек поиска")
        self._update_secretes()

    def _update_secretes(self) -> None:
        """Обновление ID пользователя на hh.ru в файле секретов"""
        secrets = load_yaml_file(self.secrets_file)
        secrets["user_id"] = self.secrets["user_id"]
        save_yaml_file(self.secrets_file, secrets)
