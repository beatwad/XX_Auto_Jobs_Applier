import os
from pathlib import Path

import pytest


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


# Test pause functionality
def test_pause(mocker):
    from src.utils.utils import pause

    mock_sleep = mocker.patch("time.sleep")
    pause(1, 2)
    assert mock_sleep.called
    assert 1 <= mock_sleep.call_args[0][0] <= 2
