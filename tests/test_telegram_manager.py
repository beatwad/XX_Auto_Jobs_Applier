from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.constants import SEARCH_CONFIG_FILE, SECRETS_FILE


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


@pytest.fixture
def mock_telegram_constants(monkeypatch):
    monkeypatch.setattr("src.constants.TG_CHAT_ID", "test_chat_id")


def test_async_telegram_report_format_jobs_no_info():
    from src.telegram.telegram_manager import TelegramReportSender

    async_telegram_report = TelegramReportSender()
    jobs_no_info = [
        {"job_title": "Job 1", "link": "http://example.com/job1", "reason": "Reason 1"},
        {"job_title": "Job 2", "link": "http://example.com/job2", "reason": "Reason 2"},
    ]
    expected = (
        "**Название вакансии:** Job 1\n"
        "**Ссылка на вакансию:** http://example.com/job1\n"
        "**Причина:** Reason 1\n\n"
        "**Название вакансии:** Job 2\n"
        "**Ссылка на вакансию:** http://example.com/job2\n"
        "**Причина:** Reason 2\n\n"
    )
    assert async_telegram_report._format_jobs_no_info(jobs_no_info) == expected


@pytest.mark.asyncio
async def test_send_telegram_report(monkeypatch):
    from src.telegram.telegram_manager import TelegramReportSender

    # Mock the asyncio.run function to prevent the "cannot be called from a running event loop" error
    async_telegram_report = TelegramReportSender()
    mock_send_message = AsyncMock()
    mock_bot = AsyncMock()
    mock_bot.send_message = mock_send_message
    async_telegram_report.bot = mock_bot
    expected_message = (
        "Email клиента: test@example.com\nФИО клиента: deanonymized deanonymized"
        "\nВсего за прошедший день на сайте hh.ru успешно откликнулись на 5 подходящих вам вакансий.\n"
        "Ниже прилагаем список вакансий, на которые ответить не получилось ввиду отсутствия информации:\n\n"
        "**Название вакансии:** Job 1\n**Ссылка на вакансию:** http://example.com/job1\n"
        "**Причина:** Reason 1\n\n\nНиже прилагаем статистику по наиболее востребованным навыкам в интересующих вас вакансиях:\n\n"
        "  Svelte: 20\n  Next.js: 19\n  Vue.js: 18\n  Angular: 17\n  Node.js: 16\n  React: 15\n  Git: 14\n  Docker: 13\n  SQL: 12\n  "
        "TypeScript: 11\n  Kotlin: 10\n  Swift: 9\n  Go: 8\n  Ruby: 7\n  PHP: 6\n  C#: 5\n  JavaScript: 4\n  Python: 3\n  Java: 2\n  C++: 2\n\n"
        "Также прилагаем рекомендации по улучшению вашего резюме:\n\nImprove your skills"
    )
    # Also patch the internal call to asyncio.run to avoid the error
    with patch("asyncio.run") as mock_asyncio_run:
        login = "test@example.com"
        resume = {
            "personal_information": {
                "telegram": "test_telegram",
                "email": "test@example.com",
                "whatsapp": "test_whatsapp",
            }
        }
        success_applies_num = "5"
        jobs_no_info = [
            {"job_title": "Job 1", "link": "http://example.com/job1", "reason": "Reason 1"}
        ]
        skill_stat = {
            "Python": 3,
            "Java": 2,
            "C++": 2,
            "JavaScript": 4,
            "C#": 5,
            "PHP": 6,
            "Ruby": 7,
            "Go": 8,
            "Swift": 9,
            "Kotlin": 10,
            "TypeScript": 11,
            "SQL": 12,
            "Docker": 13,
            "Git": 14,
            "React": 15,
            "Node.js": 16,
            "Angular": 17,
            "Vue.js": 18,
            "Next.js": 19,
            "Svelte": 20,
            "Excel": 1,
        }
        resume_recommendations = "Improve your skills"
        resume_component = MagicMock()
        resume_component.deanonymize_personal_information.return_value = "deanonymized"

        async_telegram_report.send_telegram_report(
            login,
            resume,
            success_applies_num,
            jobs_no_info,
            skill_stat,
            resume_recommendations,
            resume_component,
        )

        assert async_telegram_report.message == expected_message
        # Verify that asyncio.run was called
        assert mock_asyncio_run.called


@pytest.mark.asyncio
async def test_send_chunked_messages():
    from src.telegram.telegram_manager import TelegramReportSender

    async_telegram_report = TelegramReportSender()
    async_telegram_report.bot = AsyncMock()
    # Use the mock bot from the fixture
    header = "Header"
    # Create a message that will result in exactly 2 chunks
    # First chunk: 4096 chars
    # Second chunk: header + remaining chars
    message_body_len = 4096 - len(header)
    second_chunk_len = 100  # Small enough for a second chunk
    long_message = header + "A" * (message_body_len + second_chunk_len)

    with patch("asyncio.sleep"):
        await async_telegram_report._send_chunked_messages(long_message, header)

    # Verify first call has the right length
    first_call_text = async_telegram_report.bot.send_message.call_args_list[0][1]["text"]
    assert len(first_call_text) == 4096

    # Verify second call has the header + remaining content
    second_call_text = async_telegram_report.bot.send_message.call_args_list[1][1]["text"]
    assert second_call_text.startswith(header)
    assert len(second_call_text) == len(header) + second_chunk_len


def test_format_jobs_no_info():
    from src.telegram.telegram_manager import TelegramReportSender

    async_telegram_report = TelegramReportSender()
    jobs = [
        {"job_title": "Developer", "link": "https://example.com/job1", "reason": "Missing skills"},
        {
            "job_title": "Designer",
            "link": "https://example.com/job2",
            "reason": "Not enough experience",
        },
    ]

    result = async_telegram_report._format_jobs_no_info(jobs)

    assert "Developer" in result
    assert "Designer" in result
    assert "https://example.com/job1" in result
    assert "https://example.com/job2" in result
    assert "Missing skills" in result
    assert "Not enough experience" in result


# Tests for standalone functions
@pytest.mark.asyncio
async def test_send_captcha(monkeypatch):
    from src.telegram.telegram_manager import send_captcha

    mock_send_photo = AsyncMock()
    monkeypatch.setattr("telegram.Bot.send_photo", mock_send_photo)
    monkeypatch.setattr("builtins.open", MagicMock())  # Mock the open function
    await send_captcha("test_token", "test_chat_id", 123, "test_img_path", "test_message")
    mock_send_photo.assert_called_once()


@pytest.mark.asyncio
async def test_receive_messages(monkeypatch):
    from src.telegram.telegram_manager import receive_messages

    mock_client = AsyncMock()
    mock_get_messages = AsyncMock()
    mock_client.get_messages = mock_get_messages
    monkeypatch.setattr(
        "src.telegram.telegram_manager.TelegramClient", MagicMock(return_value=mock_client)
    )
    monkeypatch.setattr("telethon.tl.types.Message", MagicMock())

    # Mocking the return value of get_messages
    mock_message = MagicMock()
    mock_message.reply_to_msg_id = 1
    mock_message.text = "test_response"

    # Mocking the reply message
    mock_reply_message = MagicMock()
    mock_reply_message.reply_to_msg_id = 2
    mock_reply_message.text = "test_message"
    mock_get_messages.side_effect = [[mock_message], mock_reply_message]

    result = await receive_messages("123", "test_hash", "test_chat_id", 123, "test_message")
    assert result == "test_response"


def test_load_secrets(mock_load_yaml_file):
    from src.telegram.telegram_manager import load_secrets

    tg_token, tg_api_id, tg_api_hash = load_secrets(SECRETS_FILE)
    assert tg_token == "test_token"
    assert tg_api_id == "12345"
    assert tg_api_hash == "test_hash"


@pytest.mark.asyncio
async def test_process_captcha_no_listen(monkeypatch):
    from src.telegram.telegram_manager import process_captcha

    mock_send_captcha = AsyncMock()
    monkeypatch.setattr("src.telegram.telegram_manager.send_captcha", mock_send_captcha)
    await process_captcha(
        "test_token",
        "123",
        "test_hash",
        "test_chat_id",
        123,
        "test_img_path",
        "test_message",
        listen=False,
    )
    mock_send_captcha.assert_called_once()


@pytest.mark.asyncio
async def test_process_captcha_listen(monkeypatch):
    from src.telegram.telegram_manager import process_captcha

    mock_receive_messages = AsyncMock(return_value="test_response")
    monkeypatch.setattr("src.telegram.telegram_manager.receive_messages", mock_receive_messages)
    result = await process_captcha(
        "test_token",
        "123",
        "test_hash",
        "test_chat_id",
        123,
        "test_img_path",
        "test_message",
        listen=True,
    )
    assert result == "test_response"
