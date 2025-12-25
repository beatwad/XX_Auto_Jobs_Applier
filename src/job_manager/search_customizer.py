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

    def set_search_parameters(self, search_params: Dict[str, Any]) -> None:
        """Установка параметров поиска"""
        logger.info("Установка параметров поиска")
        self.search_params = search_params

    def set_resume(self, resume_id: str, resume: Dict[str, Any]) -> None:
        """Добавляем резюме для анализа."""
        self.resume_id = resume_id
        self.resume = resume

    async def start_search(self) -> None:
        """Запуск поиска вакансий"""
        await self.manager.set_advanced_search_params(self.search_params, self.resume_id)
