import os
import random
import re
import time
from pathlib import Path
from typing import Tuple

import yaml
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement

from src.logger_config import logger


class ConfigError(Exception):
    pass


chromeProfilePath = os.path.join(os.getcwd(), "chrome_profile", "hh_profile")


def load_yaml_file(yaml_path: Path) -> dict:
    """Загрузить настройки из YAML файла конфигурации"""
    try:
        with open(yaml_path, "r", encoding="UTF-8") as stream:
            return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise yaml.YAMLError(f"Ошибка в чтении файла {yaml_path}: {exc}")
    except FileNotFoundError:
        raise ConfigError(f"Файл не найден: {yaml_path}")


def save_yaml_file(yaml_path: Path, data: dict) -> None:
    """Загрузить настройки из YAML файла конфигурации"""
    with open(yaml_path, "w", encoding="UTF-8") as stream:
        yaml.safe_dump(data, stream, allow_unicode=True, default_flow_style=False)


def ensure_chrome_profile() -> str:
    """Проверяем, что профиль Chrome существует"""
    logger.info(f"Проверяем, что профиль Chrome существует по пути: {chromeProfilePath}")
    profile_dir = os.path.dirname(chromeProfilePath)
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)
        logger.debug(f"Created directory for Chrome profile: {profile_dir}")
    if not os.path.exists(chromeProfilePath):
        os.makedirs(chromeProfilePath)
        logger.debug(f"Created Chrome profile directory: {chromeProfilePath}")
    return chromeProfilePath


def chrome_browser_options() -> webdriver.ChromeOptions:
    """Задать настройки браузера Chrome, в котором будет работать Selenium"""
    logger.info("Задаем настройки Chrome")
    ensure_chrome_profile()
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("window-size=1200x800")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-autofill")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-animations")
    options.add_argument("--disable-cache")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

    prefs = {
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
    }
    options.add_experimental_option("prefs", prefs)

    if len(chromeProfilePath) > 0:
        initial_path = os.path.dirname(chromeProfilePath)
        profile_dir = os.path.basename(chromeProfilePath)
        options.add_argument("--user-data-dir=" + initial_path)
        options.add_argument("--profile-directory=" + profile_dir)
        logger.info(f"Используем профиль Chrome из папки: {chromeProfilePath}")
    else:
        options.add_argument("--incognito")
        logger.info("Используем Chrome в режиме инкогнито")

    return options


def pause(low: int = 1, high: int = 2) -> None:
    """
    Выдержать случайную паузу в диапазоне от
    low секунд до high секунд.
    Используется для имитации пользовательского поведения.
    """
    pause = round(random.uniform(low, high), 1)
    time.sleep(pause)


def sleep(sleep_interval: Tuple[int, int]) -> None:
    """Аналог _pause, но ожидание можно прервать"""
    low, high = sleep_interval
    sleep_time = random.randint(low, high)
    time_to_wait = f"{sleep_time // 60} минут, {sleep_time % 60} секунд"
    time.sleep(sleep_time)
    logger.info(f"Ожидание продлилось {time_to_wait}.")


def scroll_slow(driver: webdriver, element: WebElement, time_to_scroll_sec: float = 1.5) -> int:
    """Медленно скроллить страницу, пока не дойдем до элемента"""
    current_position = driver.execute_script("""return window.pageYOffset;""")

    # Get the element's position on the page
    try:
        element_position = element.location["y"]
    except StaleElementReferenceException:
        return current_position

    # определить размер шага, необходимый для того, чтобы
    # доскроллить до элемента за время time_to_scroll_sec
    sleep_time = 0.01
    distance_ = abs(current_position - element_position)
    step_num = time_to_scroll_sec // sleep_time + 1
    step = distance_ // step_num + 1

    # медленно скроллим до нужного нам элемента
    if current_position < element_position:
        while current_position < element_position - 30:
            current_position += step
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(sleep_time)
    else:
        while current_position > element_position + 30:
            current_position -= step
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(sleep_time)

    pause(0.1, 1)
    return current_position


def click_button(driver, element) -> None:
    """Перейти по ссылке, на которую ведет кнопка"""
    url = element.get_attribute("href")
    driver.get(url)


def enter_text(element: WebElement, text: str) -> None:
    # Пытаемся удалить предыдущий текст разными способами
    element.clear()
    entered_text = element.get_attribute("value")
    for _ in entered_text:
        element.send_keys(Keys.BACKSPACE)
    # Вводим новый текст
    element.send_keys(text)


def sanitize_text(text: str, lowercase: bool = True) -> str:
    """Очистить текст"""
    if lowercase:
        text = text.lower()
    sanitized_text = text.strip().replace('"', "").replace("\\", "")
    sanitized_text = (
        re.sub(r"[\x00-\x1F\x7F]", "", sanitized_text)
        .replace("\u2009", "")
        .replace("\xa0", " ")
        .replace("\n", " ")
        .replace("\r", "")
        .rstrip(",")
    )
    return sanitized_text
