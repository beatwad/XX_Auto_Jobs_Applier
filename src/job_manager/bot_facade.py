from typing import Any, Dict

from src.logger_config import logger


class BotState:
    """Класс состояний BotFacade"""

    def __init__(self):
        logger.info("Инициализируем класс BotState")
        self.reset()

    def reset(self):
        logger.info("Сброс состояния класса BotState")
        self.parameters_set = False
        self.search_parameters_set = False
        self.resume_set = False
        self.gpt_answerer_set = False

    def validate_state(self, required_keys):
        logger.info(f"Проверяем флаги состояний BotState: {required_keys}")
        for key in required_keys:
            if not getattr(self, key):
                logger.error(f"Проверка флагов состояний провалена, флаг {key} не установлен")
                raise ValueError(
                    f"Флаг {key.replace('_', ' ').capitalize()} должен быть установлен"
                )
        logger.info("Проверка состояний пройдена успешно")


class BotFacade:
    """Класс интерфейса с ботом"""

    def __init__(
        self,
        resume_component: Any,
        search_component: Any,
        apply_component: Any,
    ):
        logger.info("Инициализируем класс BotFacade")
        self.resume_component = resume_component  # ResumeScraper
        self.search_component = search_component  # SearchCustomizer
        self.apply_component = apply_component  # JobApplier
        self.state = BotState()
        self.resume = None
        self.resume_readable = None
        self.email = None
        self.password = None
        self.parameters = None

    async def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """Проверяем, что все параметры установлены верно"""
        logger.info("Установка параметров")
        self._validate_non_empty(parameters, "Parameters")
        self.parameters = parameters
        resume_id, resume_titles = await self.resume_component.get_resume_parameters()
        parameters["resume_id"] = resume_id
        parameters["resume_titles"] = resume_titles
        self.apply_component.set_parameters(parameters)
        self.state.parameters_set = True
        logger.info("Все параметры установлены успешно")

    async def set_resume(self) -> None:
        """Собираем информацию о резюме с сайта"""
        logger.info("Собираем информацию о резюме")
        resume_info, resume_readable = await self.resume_component.get_resume_info()
        self.resume = resume_info
        self.resume_readable = resume_readable
        self.search_component.set_resume(self.resume_component.resume_id, resume_info)
        self.apply_component.set_resume(resume_info)
        self.state.resume_set = True
        logger.info("Информация о резюме успешно собрана")

    def set_search_parameters(self, parameters: Dict[str, Any]) -> None:
        """Задаем параметры поиска"""
        logger.info("Задаем параметры поиска")
        self._validate_non_empty(parameters, "Parameters")
        self.search_component.set_advanced_search_params(parameters)
        self.state.search_parameters_set = True
        logger.info("Параметры поиска успешно установлены")

    def set_gpt_answerer(self, gpt_answerer_component: Any, parameters: Dict[str, Any]) -> None:
        """Запускаем класс для работы с LLM и обработчик резюме"""
        logger.info("Запускаем класс для работы с LLM и обработчик резюме")
        self._ensure_resume_set()
        gpt_answerer_component.set_resume(self.resume, self.resume_readable)
        gpt_answerer_component.set_search_parameters(parameters)
        self.apply_component.set_gpt_answerer(gpt_answerer_component)
        self.state.gpt_answerer_set = True
        logger.info("Класс для работы с LLM успешно запущен")

    def set_resume_generator(self, resume_generator_manager, gpt_resume_generator) -> None:
        """Запускаем класс для создания резюме"""
        logger.info("Запускаем класс для работы с LLM и обработчик резюме")
        self._ensure_resume_set()
        gpt_resume_generator.set_resume(self.resume)
        self.apply_component.set_resume_generator_manager(
            resume_generator_manager, gpt_resume_generator
        )
        logger.info("Менеджер резюме успешно запущен")

    async def start_apply(self) -> None:
        """Начинаем процесс отправки резюме"""
        self.state.validate_state(
            ["resume_set", "parameters_set", "search_parameters_set", "gpt_answerer_set"]
        )
        logger.info("Начинаем процесс поиска вакансий")
        await self.apply_component.start_applying()
        logger.info("Процесс поиска вакансий успешно завершен")

    def _validate_non_empty(self, value, name) -> None:
        """Проверяем, что поле с именем `name` не пустое"""
        logger.debug(f"Проверяем, что поле с именем {name} не пустое")
        if not value:
            logger.error(f"Проверка провалена: поле с именем {name} пустое")
            raise ValueError(f"{name} cannot be empty.")
        logger.debug(f"Проверка поле с именем {name} проведена успешно")

    def _ensure_resume_set(self) -> None:
        """Проверяем, что резюме задано"""
        logger.debug("Проверяем, что резюме задано")
        if not self.state.resume_set:
            logger.error("Резюме не задано")
            raise ValueError("Необходимо задать резюме для корректной работы.")
        logger.debug("Резюме задано")
