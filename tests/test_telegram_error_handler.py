from datetime import datetime
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

    def test_init(self):
        with patch("src.telegram.telegram_error_handler.load_yaml_file") as mock_load_yaml:
            mock_load_yaml.side_effect = [{"tg_token": "test_token"}, {"user_id": "test_user_id"}]
            with patch("src.telegram.telegram_error_handler.Bot") as mock_bot_class:
                mock_bot = MagicMock()
                mock_bot_class.return_value = mock_bot

                sink = AsyncTelegramSink()

                mock_bot_class.assert_called_once_with(token="test_token")
                assert sink.user_id == "test_user_id"
                assert sink.max_retries == 6  # Default value
                assert sink.cooldown == 60  # Default value

    @pytest.mark.asyncio
    async def test_send_with_retry_success(self, sink):
        # Use patching instead of direct attribute assignment
        sink.bot.send_message.return_value = True

        result = await sink._send_with_retry("Test message")
        assert result is True
        sink.bot.send_message.assert_called_once()
        assert "HH user id" in sink.bot.send_message.call_args[1]["text"]
        assert "Test message" in sink.bot.send_message.call_args[1]["text"]

    @pytest.mark.asyncio
    async def test_send_with_retry_failure(self, sink):
        from telegram.error import TelegramError

        # Use patching instead of direct attribute assignment
        sink.bot.send_message.side_effect = TelegramError("Test error")

        result = await sink._send_with_retry("Test message")
        assert result is False
        assert sink.bot.send_message.call_count == 2  # Two retries as configured

    @patch(
        "builtins.open", new_callable=mock_open, read_data='{"test error": "2023-01-01T00:00:00"}'
    )
    def test_is_duplicate_error_true(self, mock_file, sink):
        with patch("yaml.safe_load", return_value={"test error": "2023-01-01T00:00:00"}):
            with patch("src.telegram.telegram_error_handler.datetime") as mock_datetime:
                # Configure mock datetime to return a fixed "now"
                mock_now = MagicMock()
                mock_now.return_value = datetime.fromisoformat("2023-01-01T00:00:05")
                mock_datetime.now = mock_now
                mock_datetime.fromisoformat = datetime.fromisoformat  # Keep original function

                assert sink._is_duplicate_error("test error") is True

    @patch(
        "builtins.open", new_callable=mock_open, read_data='{"test error": "2023-01-01T00:00:00"}'
    )
    def test_is_duplicate_error_false_expired(self, mock_file, sink):
        with patch("yaml.safe_load", return_value={"test error": "2023-01-01T00:00:00"}):
            with patch("src.telegram.telegram_error_handler.datetime") as mock_datetime:
                # Configure mock datetime to return a fixed "now"
                mock_now = MagicMock()
                mock_now.return_value = datetime.fromisoformat("2023-01-01T00:15:00")
                mock_datetime.now = mock_now
                mock_datetime.fromisoformat = datetime.fromisoformat  # Keep original function

                assert sink._is_duplicate_error("test error") is False

    @patch("builtins.open", new_callable=mock_open)
    def test_update_error_cache(self, mock_file, sink):
        with patch("src.telegram.telegram_error_handler.save_yaml_file") as mock_save:
            with patch("src.telegram.telegram_error_handler.datetime") as mock_datetime:
                # Configure mock datetime to return a fixed "now"
                fixed_datetime = datetime.fromisoformat("2023-01-01T00:00:00")
                mock_now = MagicMock()
                mock_now.return_value = fixed_datetime
                mock_datetime.now = mock_now
                mock_datetime.fromisoformat = datetime.fromisoformat  # Keep original function

                sink._update_error_cache("test error")
                mock_save.assert_called_once()
                # Check the first arg is the error cache file path
                assert mock_save.call_args[0][0] == sink.error_cache_file
                # Check the second arg has the error message as key
                assert "test error" in mock_save.call_args[0][1]
                assert mock_save.call_args[0][1]["test error"] == fixed_datetime.isoformat()

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

    def test_call_method_loop_running(self, sink):
        sink._process_message = AsyncMock()
        sink.loop.is_running = MagicMock(return_value=True)
        sink.loop.create_task = MagicMock()

        sink("Test message")

        sink.loop.is_running.assert_called_once()
        sink.loop.create_task.assert_called_once()

    def test_call_method_loop_not_running(self, sink):
        sink._process_message = AsyncMock()
        sink.loop.is_running = MagicMock(return_value=False)
        sink.loop.run_until_complete = MagicMock()

        sink("Test message")

        sink.loop.is_running.assert_called_once()
        sink.loop.run_until_complete.assert_called_once()


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
