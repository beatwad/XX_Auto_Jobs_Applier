from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from src.constants import SEARCH_CONFIG_FILE, SECRETS_FILE
from src.telegram.telegram_error_handler import (
    AsyncTelegramSink,
    load_secrets,
    load_yaml_file,
    save_yaml_file,
)


# Mocking utility functions and constants
@pytest.fixture
def mock_load_yaml_file(monkeypatch):
    def mock_load(file_path):
        if file_path == SECRETS_FILE:
            return {
                "tg_token": "test_token",
                "tg_api_id": "12345",
                "tg_api_hash": "test_hash",
            }
        elif file_path == SEARCH_CONFIG_FILE:
            return {"user_id": "test_user"}
        return {}

    monkeypatch.setattr("src.telegram.telegram_manager.load_yaml_file", mock_load)


class TestYamlFunctions:
    @patch("builtins.open", new_callable=mock_open, read_data='{"tg_token": "dummy_token"}')
    def test_load_yaml_file(self, mock_file):
        result = load_yaml_file(Path("test.yaml"))
        assert result["tg_token"] == "dummy_token"

    @patch("builtins.open", new_callable=mock_open)
    @patch("yaml.safe_dump")
    def test_save_yaml_file(self, mock_dump, mock_file):
        data = {"tg_token": "dummy_token"}
        save_yaml_file(Path("test.yaml"), data)
        mock_file.assert_called_once_with(Path("test.yaml"), "w", encoding="UTF-8")
        mock_dump.assert_called_once_with(
            data, mock_file(), allow_unicode=True, default_flow_style=False
        )


class TestAsyncTelegramSink:
    @pytest.fixture
    def mock_bot(self):
        bot_mock = MagicMock()
        bot_mock.send_message = AsyncMock()
        return bot_mock

    @pytest.fixture
    def mock_yaml_load(self):
        with patch("src.telegram.telegram_error_handler.load_yaml_file") as mock:
            mock.side_effect = [
                {"tg_token": "test_token"},  # First call for secrets
                {"user_id": "test_user_id"},  # Second call for user_id
            ]
            yield mock

    @pytest.fixture
    def sink(self, mock_yaml_load, mock_bot):
        with patch("telegram.Bot", return_value=mock_bot):
            sink = AsyncTelegramSink(max_retries=2, cooldown=10)
            sink.bot = mock_bot  # Ensure the mock bot is used
            return sink

    @pytest.mark.asyncio
    async def test_process_message_new_error(self, sink):
        sink._is_duplicate_error = MagicMock(return_value=False)
        sink._send_with_retry = AsyncMock(return_value=True)
        sink._update_error_cache = MagicMock()

        await sink._process_message("Test error message")

        sink._is_duplicate_error.assert_called_once()
        sink._send_with_retry.assert_called_once_with("Test error message")
        sink._update_error_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_duplicate_error(self, sink):
        sink._is_duplicate_error = MagicMock(return_value=True)
        sink._send_with_retry = AsyncMock()
        sink._update_error_cache = MagicMock()

        await sink._process_message("Test error message")

        sink._is_duplicate_error.assert_called_once()
        sink._send_with_retry.assert_not_called()
        sink._update_error_cache.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_unknown_error(self, sink):
        sink._is_duplicate_error = MagicMock(return_value=False)
        sink._send_with_retry = AsyncMock(return_value=True)
        sink._update_error_cache = MagicMock()

        await sink._process_message("Неизвестная ошибка на странице\nActual error content")

        # Should extract the error content without the first line for caching
        sink._is_duplicate_error.assert_called_once_with("Actual error content")
        sink._send_with_retry.assert_called_once_with(
            "Неизвестная ошибка на странице\nActual error content"
        )
        sink._update_error_cache.assert_called_once()

@patch("src.telegram.telegram_error_handler.load_yaml_file")
def test_load_secrets(mock_load_yaml):
    mock_load_yaml.return_value = {
        "tg_token": "test_token",
        "tg_api_id": "test_id",
        "tg_api_hash": "test_hash",
    }

    token, api_id, api_hash = load_secrets("test/path")

    mock_load_yaml.assert_called_once_with("test/path")
    assert token == "test_token"
    assert api_id == "test_id"
    assert api_hash == "test_hash"
