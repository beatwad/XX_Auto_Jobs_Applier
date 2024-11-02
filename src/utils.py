import os
import sys

from selenium import webdriver
from loguru import logger
from src.app_config import MINIMUM_LOG_LEVEL


log_file = "app_log.log"

if MINIMUM_LOG_LEVEL in ["DEBUG", "TRACE", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    logger.remove()
    logger.add(sys.stderr, level=MINIMUM_LOG_LEVEL)
else:
    logger.warning(f"Invalid log level: {MINIMUM_LOG_LEVEL}. Defaulting to DEBUG.")
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

chromeProfilePath = os.path.join(os.getcwd(), "chrome_profile", "hh_profile")

def ensure_chrome_profile() -> str:
    """Проверяем, что профиль Chrome существует"""
    logger.debug(f"Проверяем, что профиль Chrome существует по пути: {chromeProfilePath}")
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
    logger.debug("Задаем настройки Chrome")
    ensure_chrome_profile()
    options = webdriver.ChromeOptions()
    # options.add_argument("--start-maximized")
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
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

    prefs = {
        "profile.default_content_setting_values.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
    }
    options.add_experimental_option("prefs", prefs)

    if len(chromeProfilePath) > 0:
        initial_path = os.path.dirname(chromeProfilePath)
        profile_dir = os.path.basename(chromeProfilePath)
        options.add_argument('--user-data-dir=' + initial_path)
        options.add_argument("--profile-directory=" + profile_dir)
        logger.debug(f"Используем профиль Chrome из папки: {chromeProfilePath}")
    else:
        options.add_argument("--incognito")
        logger.debug("Используем Chrome в режиме инкогнито")

    return options


def printred(text: str) -> None:
    red = "\033[91m"
    reset = "\033[0m"
    logger.debug("Печатаем текст красным: %s", text)
    print(f"{red}{text}{reset}")


def printyellow(text: str) -> None:
    yellow = "\033[93m"
    reset = "\033[0m"
    logger.debug("Печатаем текст желтым: %s", text)
    print(f"{yellow}{text}{reset}")
