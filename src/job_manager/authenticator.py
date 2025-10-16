import asyncio
import os
from datetime import datetime

import requests
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.constants import SECRETS_FILE, TG_CAPTCHA_TOPIC_ID, TG_CHAT_ID
from src.logger_config import logger
from src.telegram.telegram_manager import load_secrets, process_captcha
from src.utils.utils import pause


class Authenticator:
    """Класс для входа и получения данных для входа на сайт"""

    def __init__(self, driver=None):
        self.driver = driver
        self.login = None
        self.password = None
        logger.info(f"Аутентификатор проинициализирован драйвером: {driver}")

    def set_parameters(self, login: str, password: str) -> None:
        logger.info("Установка параметров Authenticator")
        self.login = login
        self.password = password

    def start(self) -> bool:
        logger.info("Запускаем Chrome для захода на сайт.")
        if self.is_logged_in():
            logger.info("Пользователь уже вошел на сайт, пропускаем процесс входа.")
            return True
        else:
            logger.info("Пользователь не вошел на сайт. Запускаем процесс входа.")
            return self.handle_login()

    def is_logged_in(self) -> bool:
        """Проверка того, что пользователь вошел на сайт"""
        try:
            self.driver.get("https://www.hh.ru")
            logger.info("Проверка того, что пользователь вошел на сайт...")

            logo = ("class name", "supernova-logo-wrapper")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(logo))

            # Check for the presence of the "Start a post" button
            resume_element = ("css selector", '[data-qa="mainmenu_myResumes"]')
            resumes = self.driver.find_elements(*resume_element)
            if len(resumes) > 0:
                logger.info("Нашли меню 'Мои резюме', пользователь вошел на сайт.")
                return True

            profile_element = ("css selector", '[data-qa="mainmenu_applicantProfile"]')
            profiles = self.driver.find_elements(*profile_element)
            if len(profiles) > 0:
                logger.info("Нашли меню профиля, пользователь вошел на сайт.")
                return True

            logger.warning("Не нашли меню резюме или профиля, пользователь не вошел на сайт.")
            return False

        except TimeoutException:
            logger.error(
                "Превышен лимит ожидания. Сайт недоступен или нет подключения к интернету."
            )
            return False

    def handle_login(self) -> bool:
        """Вход на сайт"""
        logger.info("Заходим на сайт...")
        self.driver.get("https://hh.ru")

        # Найти кнопку входа
        try:
            return self.enter_credentials()
        except NoSuchElementException as e:
            logger.error(f"Не можем зайти на сайт - элемент не найден: {e}")
            return False

    def enter_credentials(self) -> bool:
        """Ввод данных пользователя"""
        logger.info("Ввод данных пользователя...")
        self.driver.get("https://hh.ru/employer")
        self.driver.find_element("xpath", "//*[contains(@data-qa, 'login')]").click()
        # вводим логин
        login_element = self.driver.find_element(
            "xpath", "//*[@data-qa='login-input-username' or @data-qa='account-signup-email']"
        )
        # если поле заполнено - стираем
        entered_text = login_element.get_attribute("value")
        for _ in entered_text:
            login_element.send_keys(Keys.BACKSPACE)
        login_element.send_keys(self.login)
        # находим поле пароля
        password_switch_button = self.driver.find_elements(
            "xpath", "//*[starts-with(@data-qa, 'expand-login-by')]"
        )
        if len(password_switch_button) > 0:
            password_switch_button[0].click()
            pause()
        password_field = self.driver.find_element("xpath", "//*[@data-qa='login-input-password']")
        password_field.send_keys(self.password)
        pause()
        # входим на сайт
        submit_button = self.driver.find_element("xpath", "//*[@data-qa='account-login-submit']")
        submit_button.click()
        pause(2, 3)

        self.process_captcha(submit_button)

        if not self.check_password_is_correct():
            logger.error("Неверный пароль. Отменяем вход.")
            return False

        return True

    def check_password_is_correct(self) -> bool:
        """Проверяем, что введенный пароль корректный"""
        pause()
        login_error = self.driver.find_elements("xpath", "//*[@data-qa='account-login-error']")
        if len(login_error) > 0:
            return False
        return True

    def process_captcha(self, submit_button) -> None:
        """Обрабатываем капчу в случае появления"""
        dt_now = datetime.now()

        # проверяем, не появилась ли капча
        captcha_element = self.driver.find_elements(
            "xpath", "//*[@data-qa='account-captcha-picture']"
        )
        if len(captcha_element) > 0:
            logger.info("Обнаружили капчу, отсылаем изображение в чат")
        tg_token, tg_api_id, tg_api_hash = load_secrets(SECRETS_FILE)

        while len(captcha_element) > 0:
            if (datetime.now() - dt_now).total_seconds() > 3600:
                logger.error("Капча не решена за час, отменяем вход.")
                break

            # сперва проверяем, что пароль введен корректно
            if not self.check_password_is_correct():
                break

            captcha_filename = "captcha_image.png"
            # уникальный ID сообщения, по которому программа
            # будет идентифицировать свое сообщение в чате
            message = str(int(datetime.now().timestamp() * 10**6))
            # если изображение капчи еще не скачано - скачать его
            if not os.path.exists(captcha_filename):
                image_url = captcha_element[0].get_attribute("src")
                if not image_url:
                    break

                # Получить cookies из Selenium
                cookies = self.driver.get_cookies()
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                # Создать сессию и добавить в нее cookies
                session = requests.Session()
                for cookie in cookies:
                    session.cookies.set(cookie["name"], cookie["value"])

                # Скачать изображение капчи
                response = session.get(image_url, headers=headers)

                # Сохранить изображение
                if response.status_code == 200:
                    with open(captcha_filename, "wb") as file:
                        file.write(response.content)
                    logger.info("Изображение капчи успешно скачано.")
                else:
                    logger.error(
                        f"Ошибка при скачивании капчи. Код статуса: {response.status_code}"
                    )

                asyncio.run(
                    process_captcha(
                        tg_token,
                        tg_api_id,
                        tg_api_hash,
                        TG_CHAT_ID,
                        TG_CAPTCHA_TOPIC_ID,
                        captcha_filename,
                        message,
                    )
                )
            else:
                answer = asyncio.run(
                    process_captcha(
                        tg_token,
                        tg_api_id,
                        tg_api_hash,
                        TG_CHAT_ID,
                        TG_CAPTCHA_TOPIC_ID,
                        captcha_filename,
                        message,
                        listen=True,
                    )
                )
                captcha_element_input = self.driver.find_element(
                    "xpath", "//*[@data-qa='account-captcha-input']"
                )
                if answer:
                    logger.info("Получили расшифровку капчи из чата.")
                    captcha_element_input.send_keys(answer)
                    pause()
                    submit_button.click()
                    os.remove(captcha_filename)
                    pause(10, 10)

            captcha_element = self.driver.find_elements(
                "xpath", "//*[@data-qa='account-captcha-picture']"
            )
        else:
            logger.info("Капча решена или не появилась, продолжаем работу")
