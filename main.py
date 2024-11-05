import os
import sys
import yaml
import traceback
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from src.utils import chrome_browser_options
from src.llm.llm_manager import GPTAnswerer
from src.authenticator import Authenticator
from src.bot_facade import BotFacade
from src.job_manager import JobManager
from loguru import logger

# TODO: handle radio buttons

log_file = "log/app_log.log"
logger.add(log_file)

# Не выводить stderr
sys.stderr = open(os.devnull, 'w')

class ConfigError(Exception):
    pass

class ConfigValidator:
    """Класс для проверки правильности настроек конфигурации"""
    @staticmethod
    def load_yaml_file(yaml_path: Path) -> dict:
        """Загрузить настройки из YAML файла конфигурации"""
        try:
            with open(yaml_path, 'r', encoding="UTF-8") as stream:
                return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Ошибка в чтении файла {yaml_path}: {exc}")
        except FileNotFoundError:
            raise ConfigError(f"Файл не найден: {yaml_path}")
    
    
    def validate_search_config(self, config_yaml_path: Path) -> dict:
        """Проверить правильность настроек из файла конфигурации поиска"""
        parameters = self.load_yaml_file(config_yaml_path)
        # обязательные настройки
        required_keys = {
            'job_title': str,
            'login': str,
            'experience': dict,
            'sort_by': dict,
            'output_period': dict,
            'output_size': dict,
        }

        # Проверить, что все обязательные настройки находятся в файле настроек, а их поля имеют ожидаемый тип
        for key, expected_type in required_keys.items():
            if key not in parameters:
                    raise ConfigError(f"Отсутствует или неверный тип ключа '{key}' в конфигурационном файле {config_yaml_path}")
            elif not isinstance(parameters[key], expected_type):
                raise ConfigError(f"Неверный тип ключа '{key}' в конфигурационном файле {config_yaml_path}. Ожидается {expected_type}.")
        
        # Проверить, что все поля и значения настройки "Опыт"
        experience = ['doesnt_matter', 'no_experience', 'between_1_and_3', 'between_3_and_6', '6_and_more']
        exp_value_counter = 0
        for exp in experience:
            exp_value = parameters['experience'].get(exp)
            if not isinstance(exp_value, bool):
                raise ConfigError(f"Поле 'experience -> {exp}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
            exp_value_counter += exp_value
        if exp_value_counter > 1:
            raise ConfigError(f"Среди значение 'experience' только одно может иметь значение true в конфигурационном файле {config_yaml_path}")
        
        # Проверить, что все поля и значения настройки "Сортировка"
        sort_by = ['relevance', 'publication_time', 'salary_desc', 'salary_asc']
        sort_value_counter = 0
        for s_b in sort_by:
            sort_value = parameters['sort_by'].get(s_b)
            sort_value_counter += sort_value
            if not isinstance(sort_value, bool):
                raise ConfigError(f"Поле 'sort_by -> {s_b}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
        if sort_value_counter > 1:
            raise ConfigError(f"Среди значение 'sort_by' только одно может иметь значение true в конфигурационном файле {config_yaml_path}")
        
        # Проверить все поля и значения настройки "Выводить"
        output_period = ['all_time', 'month', 'week', 'three_days', 'one_day']
        output_value_counter = 0
        for o_p in output_period:
            output_period_value = parameters['output_period'].get(o_p)
            output_value_counter += output_period_value
            if not isinstance(output_period_value, bool):
                raise ConfigError(f"Поле 'output_value -> {o_p}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
        if output_value_counter > 1:
            raise ConfigError(f"Среди значение 'output_period' только одно может иметь значение true в конфигурационном файле {config_yaml_path}")

        # Проверить все поля и значения настройки "Показывать на странице"
        output_size = ['show_20', 'show_50', 'show_100']
        output_size_value_counter = 0
        for o_s in output_size:
            output_size_value = parameters['output_size'].get(o_s)
            output_size_value_counter += output_size_value
            if not isinstance(output_size_value, bool):
                raise ConfigError(f"Поле 'output_size -> {o_s}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
        if output_size_value_counter > 1:
            raise ConfigError(f"Среди значение 'output_size' только одно может иметь значение true в конфигурационном файле {config_yaml_path}")

        # необязательные настройки
        optional_keys = {
            'keywords' : list,
            'search_only': dict,
            'words_to_exclude' : list,
            'specialization': str,
            'industry': str,
            'regions' : list,
            'districts' : list,
            'subway' : list,
            'income': int,
            'education': dict,
            'job_type': dict,
            'work_schedule': dict,
            'side_job': dict,
            'other_params': dict,
            'job_blacklist': list,
        }

        # Проверить что все обязательные настройки находятся в файле настроек, а их поля имеют ожидаемый тип
        for key, expected_type in optional_keys.items():
            if key in parameters and not isinstance(parameters[key], expected_type):
                raise ConfigError(f"Неверный тип ключа '{key}' в конфигурационном файле {config_yaml_path}. Ожидается {expected_type}.")
        
        # Проверить все поля и значения настройки "Искать только"
        search_only_list = ['vacancy_name', 'company_name', 'vacancy_description']
        for search in search_only_list:
            if 'search_only' in parameters and not isinstance(parameters['search_only'].get(search), bool):
                raise ConfigError(f"Поле 'search_only -> {search}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
            
        # Проверить все поля и значения настройки "Образование"
        education = ['not_needed', 'middle', 'higher']
        for edu in education:
            if 'education' in parameters and not isinstance(parameters['education'].get(edu), bool):
                raise ConfigError(f"Поле 'education -> {edu}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")

        # Проверить все поля и значения настройки "Тип занятости"
        job_type = ['full_time', 'part_time', 'project', 'volunteer', 'probation', 'civil_law_contract']
        for j_t in job_type:
            if 'job_type' in parameters and not isinstance(parameters['job_type'].get(j_t), bool):
                raise ConfigError(f"Поле 'job_type -> {j_t}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")

        # Проверить все поля и значения настройки "График работы"
        work_schedule = ['full_day', 'shift', 'flexible', 'remote', 'fly_in_fly_out']
        for w_s in work_schedule:
            if 'work_schedule' in parameters and not isinstance(parameters['work_schedule'].get(w_s), bool):
                raise ConfigError(f"Поле 'work_schedule -> {w_s}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
            
        # Проверить все поля и значения настройки "Подработка"
        side_job = ['project', 'part', 'from_4_hours_per_day', 'weekend', 'evenings']
        for s_j in side_job:
            if 'side_job' in parameters and not isinstance(parameters['side_job'].get(s_j), bool):
                raise ConfigError(f"Поле 'side_job -> {s_j}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
            
        # Проверить все поля и значения настройки "Другие параметры"
        other_params = ['with_address', 'accept_handicapped', 'not_from_agency', 'accept_kids', 'accredited_it', 'low_performance']
        for o_p in other_params:
            if 'other_params' in parameters and not isinstance(parameters['other_params'].get(o_p), bool):
                raise ConfigError(f"Поле 'other_params -> {o_p}' должно иметь тип bool в конфигурационном файле {config_yaml_path}")
        
        logger.debug("Проверка параметров завершена успешно.")
        
        return parameters

    def validate_resume(self, structured_resume_path: Path) -> dict:
        """Проверить правильность полей в файле резюме"""
        parameters = self.load_yaml_file(structured_resume_path)
        required_keys = {
            'personal_information': dict,
            'legal_authorization': dict,
            'work_preferences': dict,
            'education_details': list,
            'experience_details': list,
            'projects': list,
            'availability': dict,
            'salary_expectations': dict,
            'certifications': list,
            'languages': list,
            'interests': list,
            'achievements': list,
            'previous_job_details': dict,
            'general_knowledge_questions': str,
            'skills': list,
        }

        # Проверить, что все обязательные настройки находятся в файле настроек, а их поля имеют ожидаемый тип
        for key, expected_type in required_keys.items():
            if key not in parameters:
                    raise ConfigError(f"Отсутствует или неверный тип ключа '{key}' в конфигурационном файле {structured_resume_path}")
            elif not isinstance(parameters[key], expected_type):
                raise ConfigError(f"Неверный тип ключа '{key}' в конфигурационном файле {structured_resume_path}. Ожидается {expected_type}.")
        
        # Проверить, что поля имени и фамилии есть в личной информации
        personal_information = parameters["personal_information"]
        if not personal_information:
            raise ConfigError(f"Поле 'personal_information' не может быть пустым в конфигурационном файле {structured_resume_path}")
        neccessary_fields = ['name', 'surname']
        for field in neccessary_fields:
            if not personal_information.get(field):
                raise ConfigError(f"Поле 'personal_information -> {field}' не может быть пустым в конфигурационном файле {structured_resume_path}")
        
        # Проверить, что информация о контактах есть в личной информации
        contact_fields = ['phone', 'email', 'telegram']
        for field in contact_fields:
            if field in personal_information:
                break
        else:
            raise ConfigError(f"Хотя бы одно поле 'phone', 'email' или 'telegram' из раздела 'personal_information' не должно быть пустым в конфигурационном файле {structured_resume_path}")
        
        # Проверить, что есть разрешение на работу хотя бы в одной стране
        legal_authorization = parameters["legal_authorization"]
        if not legal_authorization.get("countries"):
            raise ConfigError(f"В поле 'legal_authorization -> countries' должна присутствовать хотя бы одна страна в конфигурационном файле {structured_resume_path}")

        # Проверить что есть разрешение на работу хотя бы в одной стране
        work_preferences = parameters["work_preferences"]
        if not work_preferences.get("position"):
            raise ConfigError(f"Поле 'work_preferences -> position' не может быть пустым в конфигурационном файле {structured_resume_path}")

        # Проверить что есть информация о том, когда соискатель готов выйти на работу
        availability = parameters["availability"]
        if not availability.get("notice_period"):
            raise ConfigError(f"Поле 'availability -> notice_period' не может быть пустым в конфигурационном файле {structured_resume_path}")
        
        # Проверить что поле с желаемой зарплатой не пустое
        salary_expectations = parameters["salary_expectations"]
        if not salary_expectations.get("salary_range"):
            raise ConfigError(f"Поле 'salary_expectations -> salary_range' не может быть пустым в конфигурационном файле {structured_resume_path}")
        
        # Проверить что поле с имеющимися навыками не пустое
        skills = parameters["skills"]
        if not skills:
            raise ConfigError(f"Поле 'skills' не может быть пустым в конфигурационном файле {structured_resume_path}")

        return parameters
    
    @staticmethod
    def validate_secrets(secrets_yaml_path: Path) -> tuple:
        """Проверить наличие секретных ключей для LLM API"""
        secrets = ConfigValidator.load_yaml_file(secrets_yaml_path)
        mandatory_secrets = ['llm_api_key']

        for secret in mandatory_secrets:
            if secret not in secrets:
                raise ConfigError(f"Отсутствует ключ '{secret}' в файле {secrets_yaml_path}")

        if not secrets['llm_api_key']:
            raise ConfigError(f"Значение llm_api_key не может быть пустым в файле {secrets_yaml_path}.")
        return secrets['llm_api_key']


class FileManager:
    """"Класс для поиска и проверки содержимого файла в папке данных"""
    @staticmethod
    def validate_data_folder(app_data_folder: Path) -> tuple:
        """Проверить наличие всех необходимых файлов настроек"""
        if not app_data_folder.exists() or not app_data_folder.is_dir():
            raise FileNotFoundError(f"Папка данных не найдена: {app_data_folder}")

        required_files = ['secrets.yaml', 'search_config.yaml', 'structured_resume.yaml']
        missing_files = [file for file in required_files if not (app_data_folder / file).exists()]
        
        if missing_files:
            raise FileNotFoundError(f"Отсутствуют файлы в папке данных: {', '.join(missing_files)}")

        output_folder = app_data_folder / 'output'
        output_folder.mkdir(exist_ok=True)
        return (app_data_folder / 'secrets.yaml', app_data_folder / 'search_config.yaml', app_data_folder / 'structured_resume.yaml')
    
    @staticmethod
    def file_paths_to_dict(structured_resume_file: Path) -> dict:
        """Добавить в параметры файлы резюме"""
        if not structured_resume_file.exists():
            raise FileNotFoundError(f"Файл резюме не найден: {structured_resume_file}")

        result = {'structured_resume': structured_resume_file}

        return result


def init_driver() -> webdriver.Chrome:
    """Инициализировать Selenium driver"""
    try:
        options = chrome_browser_options()
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize browser: {str(e)}")


def create_and_run_bot(parameters, llm_api_key, resume):
    """Запустить бот"""
    driver = init_driver()
    login_component = Authenticator(driver)
    gpt_answerer_component = GPTAnswerer(parameters, llm_api_key)
    apply_component = JobManager(driver)
    bot = BotFacade(login_component, apply_component)
    bot.set_resume(resume)
    bot.set_gpt_answerer(gpt_answerer_component)
    bot.set_parameters(parameters)
    bot.start_login()
    bot.set_search_parameters()
    bot.start_apply()


def main():
    try:
        data_folder = Path("data_folder")
        secrets_file, config_file, structured_resume_file = FileManager.validate_data_folder(data_folder)
        
        config_validator = ConfigValidator()
        parameters = config_validator.validate_search_config(config_file)
        llm_api_key = config_validator.validate_secrets(secrets_file)
        resume = config_validator.validate_resume(structured_resume_file)
        
        create_and_run_bot(parameters, llm_api_key, resume)
    except ConfigError as ce:
        logger.error(f"Ошибка конфигурации: {str(ce)}")
        logger.error(f"Обратитесь к гайду по настройке приложения: https://github.com/beatwad/XX_Auto_Jobs_Applier/blob/master/README.md#Настройка")
    except FileNotFoundError as fnf:
        logger.error(f"Файл не найден: {str(fnf)}")
        logger.error("Убедитесь, что все необходимые файлы находятся в папке data_folder, подробнее здесь: https://github.com/beatwad/XX_Auto_Jobs_Applier/blob/master/README.md#Использование")
    except RuntimeError:
        tb_str = traceback.format_exc()
        logger.error(f"Runtime error: {tb_str}")
        logger.error(f"Обратитесь к гайду по ошибкам приложения: https://github.com/beatwad/XX_Auto_Jobs_Applier/blob/master/README.md#Проблемы")
    except Exception:
        tb_str = traceback.format_exc()
        logger.error(f"Неизвестная ошибка: {tb_str}")
        logger.error(f"Обратитесь к гайду по ошибкам приложения: https://github.com/beatwad/XX_Auto_Jobs_Applier/blob/master/README.md#Проблемы")

if __name__ == "__main__":
    main()
