from typing import Any, Dict

from src.logger_config import logger
from src.job_manager.playwright_manager import PlaywrightJobManager


class SearchCustomizer:
    def __init__(self, manager: PlaywrightJobManager):
        self.manager = manager
        self.resume = None
        self.resume_id = None
        # Raw search config parameters (same shape as YAML / Pydantic model_dump()).
        self.search_params: Dict[str, Any] = {}

    def set_resume(self, resume_id: str, resume: Dict[str, Any]) -> None:
        """Добавляем резюме для анализа."""
        self.resume_id = resume_id
        self.resume = resume

    async def start_search(self) -> None:
        await self.manager.start_search(self.resume_id)
        await self.manager.set_advanced_search_params(self.search_params)

    def set_advanced_search_params(self, parameters: Dict[str, Any]) -> None:
        """
        Сохраняем параметры поиска (в том же формате, что и `search_config.yaml`).

        Реальное заполнение UI происходит в `PlaywrightJobManager.set_advanced_search_params()`,
        который вызывается из `start_search()`.
        """
        logger.info("Установка параметров SearchCustomizer (raw config)")
        self.search_params = parameters or {}
        logger.info("Параметры SearchCustomizer успешно сохранены")
