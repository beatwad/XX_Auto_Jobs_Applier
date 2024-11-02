import pytest
from pathlib import Path
from main import ConfigValidator, ConfigError, FileManager, init_driver
from selenium.common.exceptions import WebDriverException
import yaml

# Mock Data for Testing
VALID_YAML_CONTENT = {
    'job_title': 'Developer',
    'login': 'user',
    'experience': {
        'doesnt_matter': True, 
        'no_experience': False,
        'between_1_and_3': False, 
        'between_3_and_6': False,
        '6_and_more': False,
        },
    'sort_by': {
        'relevance': True,
        'publication_time': False, 
        'salary_desc': False, 
        'salary_asc': False,
        },
    'output_period': {
        'all_time': True,
         'month': False, 
         'week': False, 
         'three_days': False,  
         'one_day': False, 
        },
    'output_size': {
        'show_20': True,
        'show_50': False,
        'show_100': False,
        },
    'llm_api_key': 'test_key'
}

INVALID_YAML_CONTENT = {
    'job_title': 'Developer',
    'experience': {
        'doesnt_matter': True, 
        'no_experience': True,
        'between_1_and_3': True, 
        '6_and_more': False,
        },
    'sort_by': {'relevance': True, 'salary_desc': True},
}

# Utility function to write a YAML file
def write_yaml(file_path, content):
    with open(file_path, 'w') as file:
        yaml.dump(content, file)

@pytest.fixture
def tmp_valid_config(tmp_path):
    config_file = tmp_path / "search_config.yaml"
    write_yaml(config_file, VALID_YAML_CONTENT)
    return config_file

@pytest.fixture
def tmp_invalid_config(tmp_path):
    config_file = tmp_path / "search_config.yaml"
    write_yaml(config_file, INVALID_YAML_CONTENT)
    return config_file

@pytest.fixture
def tmp_data_folder(tmp_path):
    folder = tmp_path / "data_folder"
    folder.mkdir()
    (folder / "search_config.yaml").write_text(f"{VALID_YAML_CONTENT}")
    (folder / "secrets.yaml").write_text("llm_api_key: test_key")
    (folder / "structured_resume.yaml").write_text("test resume")
    return folder

@pytest.fixture
def tmp_invalid_data_folder(tmp_path):
    folder = tmp_path / "data_folder"
    folder.mkdir()
    # Missing required files
    return folder

# Test ConfigValidator.load_yaml_file()
def test_load_yaml_file(tmp_valid_config):
    config = ConfigValidator.load_yaml_file(tmp_valid_config)
    assert config['job_title'] == 'Developer'

def test_load_yaml_file_not_found():
    with pytest.raises(ConfigError):
        ConfigValidator.load_yaml_file(Path("nonexistent_file.yaml"))

# Test ConfigValidator.validate_search_config()
def test_validate_search_config_valid(tmp_valid_config):
    config_validator = ConfigValidator()
    config = config_validator.validate_search_config(tmp_valid_config)
    assert config['job_title'] == 'Developer'

def test_validate_search_config_invalid(tmp_invalid_config):
    config_validator = ConfigValidator()
    with pytest.raises(ConfigError):
        config_validator.validate_search_config(tmp_invalid_config)

# Test ConfigValidator.validate_secrets()
def test_validate_secrets(tmp_data_folder):
    secrets_file = tmp_data_folder / "secrets.yaml"
    llm_api_key = ConfigValidator.validate_secrets(secrets_file)
    assert llm_api_key == "test_key"

def test_validate_secrets_missing_key(tmp_path):
    secrets_file = tmp_path / "secrets.yaml"
    secrets_file.write_text("some_other_key: value")
    with pytest.raises(ConfigError):
        ConfigValidator.validate_secrets(secrets_file)

# Test FileManager.validate_data_folder()
def test_validate_data_folder_valid(tmp_data_folder):
    secrets_file, config_file, structured_resume = FileManager.validate_data_folder(tmp_data_folder)
    assert secrets_file.exists()
    assert config_file.exists()
    assert structured_resume.exists()

def test_validate_data_folder_missing_files(tmp_invalid_data_folder):
    with pytest.raises(FileNotFoundError):
        FileManager.validate_data_folder(tmp_invalid_data_folder)

# Test init_driver() - This will require mocking Selenium's webdriver due to dependencies on external services.
def test_init_driver(mocker):
    mocker.patch("src.utils.chrome_browser_options")
    mocker.patch("selenium.webdriver.Chrome")
    mocker.patch("selenium.webdriver.chrome.service.Service.__init__", return_value=None)
    mocker.patch("webdriver_manager.chrome.ChromeDriverManager.install", return_value="/path/to/chromedriver")

    driver = init_driver()
    assert driver is not None

def test_init_driver_exception(mocker):
    mocker.patch("src.utils.chrome_browser_options")
    mocker.patch("selenium.webdriver.Chrome")
    mocker.patch("selenium.webdriver.chrome.service.Service.__init__", side_effect=WebDriverException("Browser init failed"))
    mocker.patch("webdriver_manager.chrome.ChromeDriverManager.install", return_value="/path/to/chromedriver")
    with pytest.raises(RuntimeError):
      init_driver()
