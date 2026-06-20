import os
import sys
import random
import re
import time
from pathlib import Path
from typing import Tuple

import yaml

from src.logger_config import logger
from src.constants import APP_CONFIG_FILE

chromeProfilePath = os.path.join(os.getcwd(), "chrome_profile", "hh_profile")


class ConfigError(Exception):
    pass


def load_yaml_file(yaml_path: Path) -> dict:
    """Загрузить данные из YAML файла"""
    try:
        with open(yaml_path, "r", encoding="UTF-8") as stream:
            return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise yaml.YAMLError(f"Ошибка в чтении файла {yaml_path}: {exc}")
    except FileNotFoundError:
        # We can't log here because of circular dependency with logger
        # raise ConfigError(f"Файл не найден: {yaml_path}")
        # Or just raise it and let caller handle
        raise ConfigError(f"Файл не найден: {yaml_path}")


def load_app_config() -> dict:
    """Загрузить конфигурацию приложения из YAML файла"""
    try:
        config = load_yaml_file(APP_CONFIG_FILE)
        return config or {}
    except Exception as e:
        # Fallback logging to stderr since we can't use logger here
        print(f"Ошибка при загрузке конфигурации приложения: {e}", file=sys.stderr)
        return {}


def save_yaml_file(yaml_path: Path, data: dict, sort_keys: bool = True) -> None:
    """Сохранить данные в YAML файл"""
    with open(yaml_path, "w", encoding="UTF-8") as stream:
        yaml.safe_dump(
            data, stream, allow_unicode=True, default_flow_style=False, sort_keys=sort_keys
        )


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
