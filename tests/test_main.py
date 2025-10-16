from pathlib import Path

import pytest
import yaml


@pytest.fixture
def temp_data_folder(tmp_path):
    """Create a temporary data folder with required structure"""
    data_folder = tmp_path / "data_folder"
    secrets_folder = data_folder / "secrets"
    config_folder = data_folder / "search_config"

    secrets_folder.mkdir(parents=True)
    config_folder.mkdir(parents=True)

    return data_folder


@pytest.fixture
def valid_search_config():
    return {
        "job_title": "Software Engineer",
        "max_applies_num": 10,
        "experience": {
            "doesntMatter": False,
            "noExperience": True,
            "between1And3": False,
            "between3And6": False,
            "moreThan6": False,
        },
        "order_by": {
            "relevance": True,
            "publication_time": False,
            "salary_desc": False,
            "salary_asc": False,
        },
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "tariff": "1day",
    }


@pytest.fixture
def valid_secrets():
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "hh_login": "test_login",
        "hh_password": "test_password",
        "llm_api_key": "test_key",
        "llm_proxy": ["proxy1", "proxy2"],
        "tg_token": "test_token",
        "tg_api_id": "test_id",
        "tg_api_hash": "test_hash",
    }


class TestConfigValidator:
    def test_valid_search_config(self, temp_data_folder, valid_search_config, valid_secrets):
        from main import ConfigValidator

        config_file = temp_data_folder / "search_config.yaml"
        config_file_tmp = temp_data_folder / "search_config.yaml"

        expected = {
            "job_title": "Software Engineer",
            "user_id": "",
            "resume_id": "",
            "keywords": "",
            "max_applies_num": 10,
            "max_total_applies_num": 1500,
            "experience": {
                "doesntMatter": False,
                "noExperience": True,
                "between1And3": False,
                "between3And6": False,
                "moreThan6": False,
            },
            "employment": None,
            "search_field": None,
            "words_to_exclude": "",
            "professional_role": "",
            "industry": "",
            "area": "",
            "districts": "",
            "metro": "",
            "salary": None,
            "only_with_salary": None,
            "currency": None,
            "education": None,
            "schedule": None,
            "part_time": None,
            "vacancy_label": None,
            "job_blacklist": [],
            "order_by": {
                "relevance": True,
                "publication_time": False,
                "salary_desc": False,
                "salary_asc": False,
            },
            "period": None,
            "cover_letter": None,
            "apply_once_at_company": True,
            "skip_companies_with_test": False,
        }

        with open(config_file, "w") as f:
            yaml.dump(valid_search_config, f)

        validator = ConfigValidator()
        result = validator.validate_search_config(config_file, config_file_tmp, valid_secrets)

        # Verify the result matches the input
        assert result == expected

    # Test removed: SearchConfig has no truly required fields (all have defaults or are Optional)
    # def test_invalid_search_config_missing_required(
    #     self, temp_data_folder, valid_search_config, valid_secrets
    # ):
    #     from main import ConfigError, ConfigValidator
    #
    #     invalid_config = valid_search_config.copy()
    #     del invalid_config["tariff"]  # Remove a required field
    #
    #     config_file = temp_data_folder / "search_config.yaml"
    #     config_file_tmp = temp_data_folder / "search_config.yaml.tmp"
    #
    #     with open(config_file, "w") as f:
    #         yaml.dump(invalid_config, f)
    #
    #     validator = ConfigValidator()
    #     with pytest.raises(ConfigError, match="Ошибка валидации конфигурации"):
    #         validator.validate_search_config(config_file, config_file_tmp, valid_secrets)

    # def test_invalid_search_config_multiple_experience(
    #     self, temp_data_folder, valid_search_config, valid_secrets
    # ):
    #     from main import ConfigError, ConfigValidator

    #     invalid_config = valid_search_config.copy()
    #     invalid_config["experience"] = {"doesntMatter": True, "noExperience": True}

    #     config_file = temp_data_folder / "search_config.yaml"
    #     config_file_tmp = temp_data_folder / "search_config.yaml.tmp"

    #     with open(config_file, "w") as f:
    #         yaml.dump(invalid_config, f)

    #     validator = ConfigValidator()
    #     with pytest.raises(ConfigError, match="Ошибка валидации конфигурации"):
    #         validator.validate_search_config(config_file, config_file_tmp, valid_secrets)

    def test_valid_secrets(self, temp_data_folder, valid_secrets):
        from main import ConfigValidator

        secrets_file = temp_data_folder / "secrets" / "secrets.yaml"
        with open(secrets_file, "w") as f:
            yaml.dump(valid_secrets, f)

        validator = ConfigValidator()
        result = validator.validate_secrets(secrets_file)
        assert result == valid_secrets

    def test_missing_secret_key(self, temp_data_folder, valid_secrets):
        from main import ConfigError, ConfigValidator

        invalid_secrets = valid_secrets.copy()
        del invalid_secrets["llm_api_key"]

        secrets_file = temp_data_folder / "secrets" / "secrets.yaml"
        with open(secrets_file, "w") as f:
            yaml.dump(invalid_secrets, f)

        validator = ConfigValidator()
        with pytest.raises(ConfigError, match="Ошибка валидации секретов"):
            validator.validate_secrets(secrets_file)


class TestFileManager:
    def test_valid_data_folder(self, temp_data_folder):
        from main import FileManager

        # Create required files
        (temp_data_folder / "secrets" / "secrets.yaml").touch()
        (temp_data_folder / "search_config" / "search_config.yaml").touch()

        FileManager.validate_data_folder(temp_data_folder)
        assert (temp_data_folder / "output").exists()

    def test_missing_data_folder(self):
        from main import FileManager

        with pytest.raises(FileNotFoundError, match="Папка данных не найдена"):
            FileManager.validate_data_folder(Path("nonexistent_folder"))

    def test_missing_required_files(self, temp_data_folder):
        from main import FileManager

        with pytest.raises(FileNotFoundError, match="Отсутствуют файлы в папке данных"):
            FileManager.validate_data_folder(temp_data_folder)
