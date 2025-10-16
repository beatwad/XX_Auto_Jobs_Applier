import os
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement


# Fixtures
@pytest.fixture
def sample_yaml_file(tmp_path):
    yaml_content = """
    key1: value1
    key2: value2
    """
    yaml_file = tmp_path / "test_config.yaml"
    yaml_file.write_text(yaml_content)
    return yaml_file


@pytest.fixture
def mock_webdriver(mocker):
    return mocker.Mock(spec=webdriver.Chrome)


@pytest.fixture
def mock_webelement(mocker):
    return mocker.Mock(spec=WebElement)


# Test YAML loading
def test_load_yaml_file_success(sample_yaml_file):
    from src.utils.utils import load_yaml_file

    result = load_yaml_file(sample_yaml_file)
    assert isinstance(result, dict)
    assert result["key1"] == "value1"
    assert result["key2"] == "value2"


def test_load_yaml_file_not_found():
    from src.utils.utils import load_yaml_file

    with pytest.raises(Exception):
        load_yaml_file(Path("nonexistent.yaml"))


# Test Chrome profile management
def test_ensure_chrome_profile(tmp_path, monkeypatch):
    from src.utils.utils import ensure_chrome_profile

    test_profile_path = str(tmp_path / "chrome_profile" / "test_profile")
    monkeypatch.setattr("src.utils.utils.chromeProfilePath", test_profile_path)

    result = ensure_chrome_profile()
    assert os.path.exists(test_profile_path)
    assert result == test_profile_path


def test_chrome_browser_options():
    from src.utils.utils import chrome_browser_options

    options = chrome_browser_options()
    assert isinstance(options, webdriver.ChromeOptions)

    # Check some important options are set
    arguments = options.arguments
    assert "--start-maximized" in arguments
    assert "--no-sandbox" in arguments
    assert "--disable-dev-shm-usage" in arguments


# Test pause functionality
def test_pause(mocker):
    from src.utils.utils import pause

    mock_sleep = mocker.patch("time.sleep")
    pause(1, 2)
    assert mock_sleep.called
    assert 1 <= mock_sleep.call_args[0][0] <= 2


# Test scroll functionality
def test_scroll_slow_element_below(mock_webdriver, mock_webelement):
    from src.utils.utils import scroll_slow

    mock_webelement.location = {"y": 500}
    mock_webdriver.execute_script.return_value = 0  # Current scroll position

    scroll_slow(mock_webdriver, mock_webelement, time_to_scroll_sec=0.1)

    assert mock_webdriver.execute_script.called


# Test text input
def test_enter_text(mock_webelement):
    from src.utils.utils import enter_text

    test_text = "test input"
    mock_webelement.get_attribute.return_value = "old text"

    enter_text(mock_webelement, test_text)

    assert mock_webelement.clear.called
    assert mock_webelement.send_keys.called
    mock_webelement.send_keys.assert_any_call(test_text)
