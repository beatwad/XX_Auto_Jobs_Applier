import asyncio
import logging
import random
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict

import yaml

from src.constants import (
    LOGS_DIR,
    SEARCH_CONFIG_FILE,
    SECRETS_FILE,
)
from telegram import Bot
from telegram.error import TelegramError

# Configure standard logging for internal errors
logging.basicConfig(level=logging.WARNING)
internal_logger = logging.getLogger("AsyncTelegramSink")
log_file_path = os.path.join(LOGS_DIR, "internal_logger.log")  # Path to the log file

os.makedirs(LOGS_DIR, exist_ok=True)

file_handler = logging.FileHandler(log_file_path, mode="a")  # Append mode
file_handler.setLevel(logging.WARNING)  # Set the logging level for the file handler
# Create a formatter for the log messages
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(formatter)
# Add the file handler to the internal_logger
internal_logger.addHandler(file_handler)


def load_yaml_file(yaml_path: Path) -> dict:
    """Загрузить настройки из YAML файла конфигурации"""
    try:
        with open(yaml_path, "r", encoding="UTF-8") as stream:
            return yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        internal_logger.error(f"Ошибка в чтении файла {yaml_path}: {exc}")
        raise yaml.YAMLError(f"Ошибка в чтении файла {yaml_path}: {exc}")


def save_yaml_file(yaml_path: Path, data: dict) -> None:
    """Загрузить настройки из YAML файла конфигурации"""
    with open(yaml_path, "w", encoding="UTF-8") as stream:
        yaml.safe_dump(data, stream, allow_unicode=True, default_flow_style=False)


class AsyncTelegramSink:
    """
    Класс для отправки сообщений об ошибке через Telegram.
    В случае ошибки в процессе отправки ждем и отправляем заново.
    """

    def __init__(
        self,
        max_retries: int = 6,
        cooldown: int = 60,
    ):
        secrets = load_yaml_file(SECRETS_FILE)
        telegram_bot_token = secrets["tg_token"]
        self.bot = Bot(token=telegram_bot_token)
        self.chat_id = secrets["tg_chat_id"]
        self.err_topic_id = secrets["tg_err_topic_id"]
        self.report_topic_id = secrets["tg_report_topic_id"]
        self.user_id = load_yaml_file(SEARCH_CONFIG_FILE).get("user_id", "-1")
        self.max_retries = max_retries
        self.cooldown = cooldown  # Seconds between identical error notifications
        self.error_cache_file = "src/telegram/error_cache.yaml"

        # Ensure proper async loop handling
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()

    async def _send_with_retry(self, message: str) -> bool:
        """Пытаемся отправить сообщение. В случае ошибки ждем экспоненциально дольше."""
        base_delay = 1
        # ограничиваем максимальную длину сообщения, чтобы избежать ошибки Telegram
        message_ = f"HH user id: ```{self.user_id}```\nError:\n```{message[:4050]}```"
        for attempt in range(self.max_retries):
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    message_thread_id=self.err_topic_id,
                    text=message_,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return True
            except TelegramError as e:
                if attempt == self.max_retries - 1:
                    internal_logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    return False

                delay = base_delay * (2**attempt) + random.uniform(0, 1)
                internal_logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        return False

    def _is_duplicate_error(self, new_error: str) -> bool:
        """Проверяем, чтобы похожие ошибки не отправлялись"""
        try:
            with open(self.error_cache_file, "r") as f:
                cache: Dict[str, str] = yaml.safe_load(f) or {}

            if new_error in cache:
                last_sent = datetime.fromisoformat(cache[new_error])
                return (datetime.now() - last_sent).total_seconds() < self.cooldown

        except (FileNotFoundError, yaml.YAMLError) as e:
            internal_logger.warning(f"Error reading cache: {e}")

        return False

    def _update_error_cache(self, error: str) -> None:
        """Update error timestamp in cache"""
        cache = {}
        cache[error] = datetime.now().isoformat()
        try:
            save_yaml_file(self.error_cache_file, cache)
        except (IOError, yaml.YAMLError) as e:
            internal_logger.error(f"Failed to update error cache: {e}")

    async def _process_message(self, message: str) -> None:
        """Main message processing logic"""
        try:
            # Extract error content and check for duplicates
            error_content = message.strip()
            # если сообщение начинается с "Неизвестная ошибка на странице", то удаляем первую строку,
            # чтобы в сообщении не было менящихся элементов вроде URL
            if error_content.startswith("Неизвестная ошибка на странице"):
                error_cache = error_content.split("\n")[1:]
                error_cache = "\n".join(error_cache)
            else:
                error_cache = error_content

            if self._is_duplicate_error(error_cache):
                internal_logger.info("Duplicate error suppressed")
                return

            # Attempt to send with retries
            success = await self._send_with_retry(error_content)

            if success:
                self._update_error_cache(error_cache)
            else:
                internal_logger.error("All retry attempts failed")

        except Exception:
            tb_str = traceback.format_exc()
            internal_logger.error(f"Critical error in message processing: {tb_str}")

    def __call__(self, message: str) -> None:
        """Loguru sink entry point"""
        try:
            if self.loop.is_running():
                # If loop is already running, create a task
                self.loop.create_task(self._process_message(message))
            else:
                # Run in a new loop if necessary
                self.loop.run_until_complete(self._process_message(message))
        except Exception:
            tb_str = traceback.format_exc()
            internal_logger.error(f"Failed to schedule Telegram message: {tb_str}")


def load_secrets(secrets_yaml_path: str):
    """Загружаем необходимые для работы Telegram бота ключи"""
    secrets = load_yaml_file(secrets_yaml_path)
    tg_token, tg_api_id, tg_api_hash = (
        secrets["tg_token"],
        secrets.get("tg_api_id"),
        secrets.get("tg_api_hash"),
    )
    return tg_token, tg_api_id, tg_api_hash
