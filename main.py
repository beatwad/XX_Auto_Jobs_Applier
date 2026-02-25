import asyncio
import traceback
from pathlib import Path
from typing import List

from src.constants import SEARCH_CONFIG_FILE, SEARCH_CONFIG_FILE_TMP, SECRETS_FILE
from src.job_manager.bot_facade import BotFacade
from src.job_manager.job_applier import JobApplier
from src.job_manager.playwright_manager import PlaywrightJobManager
from src.job_manager.resume_scraper import ResumeScraper
from src.job_manager.search_customizer import SearchCustomizer
from src.llm.llm_manager import GPTAnswerer
from src.logger_config import logger
from src.views.config import SearchConfig, Secrets
from src.utils.utils import load_yaml_file


# TODO: translate all comments and logs to Russian
# TODO: actualize tests


class ConfigError(Exception):
    pass


class ConfigValidator:
    """Класс для проверки правильности настроек конфигурации"""

    def validate_search_config(
        self, config_yaml_path: Path, config_yaml_path_tmp: Path, secrets: dict
    ) -> dict:
        """Проверить правильность настроек из файла конфигурации поиска"""
        parameters = load_yaml_file(config_yaml_path)

        try:
            # Преобразование параметров в нужные типы
            for key, value in parameters.items():
                if value == "None" or value == "":
                    if key == "job_blacklist":
                        parameters[key] = []
                    else:
                        parameters[key] = None

            # Валидация параметров с помощью Pydantic
            print(f"parameters: {parameters}")
            config = SearchConfig(**parameters)
            logger.debug("Проверка параметров завершена успешно.")
            return config.model_dump()

        except Exception as e:
            raise ConfigError(f"Ошибка валидации конфигурации: {str(e)}")

    @staticmethod
    def validate_secrets(secrets_yaml_path: Path) -> dict:
        """Проверить наличие секретных ключей для LLM API"""
        secrets = load_yaml_file(secrets_yaml_path)

        try:
            secrets_config = Secrets(**secrets)
            return secrets_config.model_dump()
        except Exception as e:
            raise ConfigError(f"Ошибка валидации секретов: {str(e)}")


class FileManager:
    """Класс для поиска и проверки содержимого файла в папке данных"""

    @staticmethod
    def validate_data_folder(app_data_folder: Path) -> None:
        """Проверить наличие всех необходимых файлов настроек"""
        if not app_data_folder.exists() or not app_data_folder.is_dir():
            raise FileNotFoundError(f"Папка данных не найдена: {app_data_folder}")

        required_files = ["secrets.yaml", "search_config.yaml"]
        missing_files = [
            file for file in required_files if not (app_data_folder / file[:-5] / file).exists()
        ]

        if missing_files:
            raise FileNotFoundError(f"Отсутствуют файлы в папке данных: {', '.join(missing_files)}")

        output_folder = app_data_folder / "output"
        output_folder.mkdir(exist_ok=True)


async def create_and_run_bot(
    secrets: dict, parameters: dict, llm_api_key: str, llm_proxy: List[str]
):
    """Запустить бот"""
    if secrets.get("hh_login") and secrets.get("hh_password"):
        parameters["hh_login"] = secrets["hh_login"]
        parameters["hh_password"] = secrets["hh_password"]

    job_title = parameters.get("job_title")

    manager = PlaywrightJobManager(secrets)
    await manager.initialize()

    try:
        gpt_answerer_component = GPTAnswerer(llm_api_key, llm_proxy)
        resume_component = ResumeScraper(
            manager, job_title, parameters.get("resume_id"), gpt_answerer_component
        )
        search_component = SearchCustomizer(manager)
        apply_component = JobApplier(manager, resume_component, search_component)

        bot = BotFacade(resume_component, search_component, apply_component)
        await bot.set_parameters(parameters)
        if not apply_component.check_the_last_search_time():
            logger.warning("Последний поиск был меньше суток назад, завершаем работу")
            return
        await bot.set_resume()
        bot.set_search_parameters(parameters)
        bot.set_gpt_answerer(gpt_answerer_component, parameters)
        # bot.set_resume_generator(resume_generator_manager, gpt_resume_genarator)
        await bot.start_apply()
    finally:
        await manager.close()


async def main() -> None:
    try:
        data_folder = Path("data_folder")
        FileManager.validate_data_folder(data_folder)

        config_validator = ConfigValidator()
        secrets = config_validator.validate_secrets(SECRETS_FILE)
        parameters = config_validator.validate_search_config(
            SEARCH_CONFIG_FILE, SEARCH_CONFIG_FILE_TMP, secrets
        )

        llm_api_key = secrets["llm_api_key"]
        llm_proxy = secrets["llm_proxy"]

        await create_and_run_bot(secrets, parameters, llm_api_key, llm_proxy)

        # Ждем в сумме 1 час перед следующим запуском
        # await asyncio.sleep(3000) # blocking wait in async? better use asyncio.sleep

    except ConfigError as ce:
        logger.error(f"Ошибка конфигурации: {str(ce)}")
    except FileNotFoundError as fnf:
        logger.error(f"Файл не найден: {str(fnf)}")
    except RuntimeError:
        tb_str = traceback.format_exc()
        logger.error(f"Runtime error\n{tb_str}")
    except Exception:
        tb_str = traceback.format_exc()
        logger.error(f"Неизвестная ошибка\n{tb_str}")
    finally:
        # time.sleep(600)
        pass


if __name__ == "__main__":
    asyncio.run(main())
