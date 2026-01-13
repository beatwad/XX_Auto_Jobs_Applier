import os
import sys

from loguru import logger

from src.constants import LOGS_DIR
from src.telegram.telegram_error_handler import AsyncTelegramSink

MINIMUM_LOG_LEVEL = "DEBUG"

logger.remove()

if MINIMUM_LOG_LEVEL in ["DEBUG", "TRACE", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    minimum_log_level = MINIMUM_LOG_LEVEL
else:
    minimum_log_level = "DEBUG"

# Вывод в терминал без tracebacks
logger.add(sys.stdout, level=minimum_log_level, backtrace=False, diagnose=False)

# Добавляем канал логирования (Telegram чат)
logger.add(
    AsyncTelegramSink(
        max_retries=6,
        cooldown=600,  # в случае одной и той же ошибки ждем 10 минут
    ),
    level="ERROR",
    format="{message}",
    backtrace=True,
    diagnose=True,
)

# Конфигурация логирования в файл
logger.add(
    os.path.join(LOGS_DIR, "app.log"),
    rotation="10 MB",  # Очищаем файлы при достижении 10 MB
    retention="10 days",  # Храним логи 10 дней
    compression="zip",  # Сжимаем файлы
    level=minimum_log_level,
    backtrace=True,
    diagnose=True,
)

# Конфигурация логирования ошибок в файл
logger.add(
    os.path.join(LOGS_DIR, "error.log"),
    rotation="5 MB",  # Очищаем файлы при достижении 10 MB
    retention="30 days",  # Храним ошибки 30 дней
    compression="zip",
    level="ERROR",
    backtrace=True,
    diagnose=True,
)
