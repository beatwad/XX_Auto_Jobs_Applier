import os
import sys

from loguru import logger

from src.app_config import MINIMUM_LOG_LEVEL
from src.telegram.telegram_error_handler import AsyncTelegramSink

# Не выводить stderr
sys.stderr = open(os.devnull, "w")

# Create logs directory if it doesn't exist
logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)

logger.remove()

if MINIMUM_LOG_LEVEL in ["DEBUG", "TRACE", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    minimum_log_level = MINIMUM_LOG_LEVEL
else:
    minimum_log_level = "DEBUG"

# Terminal output without tracebacks
logger.add(sys.stderr, level=minimum_log_level, backtrace=False, diagnose=False)
logger.add(sys.stdout, level=minimum_log_level, backtrace=False, diagnose=False)

# Добавить канал логирования (Telegram чат)
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
    os.path.join(logs_dir, "app.log"),
    rotation="500 MB",  # Rotate when file reaches 500 MB
    retention="10 days",  # Keep logs for 10 days
    compression="zip",  # Compress rotated logs
    level=minimum_log_level,
    backtrace=True,
    diagnose=True,
)

# Конфигурация логирования ошибок в файл
logger.add(
    os.path.join(logs_dir, "error.log"),
    rotation="100 MB",  # Rotate when file reaches 100 MB
    retention="30 days",  # Keep error logs longer
    compression="zip",
    level="ERROR",
    backtrace=True,
    diagnose=True,
)
