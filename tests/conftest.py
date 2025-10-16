import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


def pytest_collection_modifyitems(items):
    """Set custom markers for tests"""
    for item in items:
        # Mark all tests in the authenticator test file as 'authenticator'
        if "test_authenticator" in item.module.__name__:
            item.add_marker(pytest.mark.authenticator)


@pytest.fixture(autouse=True)
def mock_env_variables(monkeypatch):
    """Set mock environment variables for tests"""
    monkeypatch.setenv("MINIMUM_LOG_LEVEL", "INFO")


@pytest.fixture(scope="session", autouse=True)
def mock_telegram_sink_init():
    """
    Mock AsyncTelegramSink.__init__ at session level to handle module-level logger initialization.
    """
    with patch(
        "src.telegram.telegram_error_handler.AsyncTelegramSink.__init__",
        return_value=None,
    ):
        yield


@pytest.fixture(autouse=True)
def mock_telegram_sink(request):
    """
    Mock AsyncTelegramSink to prevent sending actual messages during tests.
    This fixture is applied automatically to all tests except telegram_error_handler tests.
    """
    # Skip this fixture for test_telegram_error_handler.py
    if (
        "test_telegram_error_handler" in request.module.__name__
        or "test_telegram_manager" in request.module.__name__
    ):
        yield None
    else:
        with patch(
            "src.telegram.telegram_error_handler.AsyncTelegramSink.__call__", return_value=None
        ) as mock_call:
            yield mock_call


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment variables and ensure directories exist"""
    # Save original environment
    old_env = os.environ.copy()

    # Create test directories if they don't exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data_folder/secrets", exist_ok=True)
    os.makedirs("data_folder/search_config", exist_ok=True)
    os.makedirs("data_folder/output", exist_ok=True)
    os.makedirs("src/telegram", exist_ok=True)

    secrets_path = Path("data_folder/secrets/secrets.yaml")
    search_config_path = Path("data_folder/search_config/search_config.yaml")
    error_cache_path = Path("src/telegram/error_cache.yaml")

    secrets_path_exists = secrets_path.exists()
    search_config_path_exists = search_config_path.exists()
    error_cache_path_exists = error_cache_path.exists()

    # Create a secrets.yaml file if it doesn't exist
    if not secrets_path_exists:
        with open(secrets_path, "w") as f:
            yaml.dump(
                {
                    "tg_token": "test_token_12345",
                    "tg_api_id": "test_api_id",
                    "tg_api_hash": "test_api_hash",
                },
                f,
            )

    # Create a search_config.yaml file if it doesn't exist
    if not search_config_path_exists:
        with open(search_config_path, "w") as f:
            yaml.dump({"user_id": "test_user"}, f)

    # Create an empty error cache file if needed for tests
    if not error_cache_path_exists:
        error_cache_path.touch()

    yield

    # Cleanup: remove test directories and files after tests
    if not secrets_path_exists:
        secrets_path.unlink(missing_ok=True)
    if not search_config_path_exists:
        search_config_path.unlink(missing_ok=True)
    if not error_cache_path_exists:
        error_cache_path.unlink(missing_ok=True)

    # Restore original environment
    os.environ.clear()
    os.environ.update(old_env)
