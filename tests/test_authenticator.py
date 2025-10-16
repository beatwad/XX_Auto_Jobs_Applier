from unittest.mock import MagicMock, patch

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from src.constants import SECRETS_FILE


@pytest.fixture
def mock_driver():
    """Mock the Selenium WebDriver"""
    driver = MagicMock()
    # Mock find_element and find_elements methods
    driver.find_element.return_value = MagicMock()
    driver.find_elements.return_value = []
    return driver


@pytest.fixture
def authenticator(mock_driver):
    """Create an Authenticator instance with a mock driver"""
    from src.job_manager.authenticator import Authenticator

    auth = Authenticator(driver=mock_driver)
    auth.set_parameters(login="test_login", password="test_password")
    return auth


@patch("src.job_manager.authenticator.WebDriverWait")
def test_is_logged_in_true(mock_wait, authenticator, mock_driver):
    """Test is_logged_in when user is logged in"""
    # Mock finding the resume element
    resume_element = MagicMock()
    mock_driver.find_elements.return_value = [resume_element]

    result = authenticator.is_logged_in()

    # Verify
    assert result is True
    mock_driver.get.assert_called_once_with("https://www.hh.ru")


@patch("src.job_manager.authenticator.WebDriverWait")
def test_is_logged_in_false(mock_wait, authenticator, mock_driver):
    """Test is_logged_in when user is not logged in"""
    # Mock not finding any elements
    mock_driver.find_elements.return_value = []

    result = authenticator.is_logged_in()

    # Verify
    assert result is False
    mock_driver.get.assert_called_once_with("https://www.hh.ru")


@patch("src.telegram.telegram_error_handler.AsyncTelegramSink.__call__", return_value=None)
@patch("src.job_manager.authenticator.WebDriverWait")
def test_is_logged_in_timeout(mock_wait, mock_telegram_sink, authenticator, mock_driver):
    """Test is_logged_in when timeout occurs"""
    # Mock timeout exception
    mock_wait.return_value.until.side_effect = TimeoutException()

    result = authenticator.is_logged_in()

    # Verify
    assert result is False
    mock_driver.get.assert_called_once_with("https://www.hh.ru")


@patch("src.job_manager.authenticator.Authenticator.enter_credentials")
def test_handle_login_success(mock_enter_credentials, authenticator, mock_driver):
    """Test handle_login success case"""
    mock_enter_credentials.return_value = True

    result = authenticator.handle_login()

    # Verify
    assert result is True
    mock_driver.get.assert_called_once_with("https://hh.ru")
    mock_enter_credentials.assert_called_once()


@patch("src.telegram.telegram_error_handler.AsyncTelegramSink.__call__", return_value=None)
@patch("src.job_manager.authenticator.Authenticator.enter_credentials")
def test_handle_login_element_not_found(
    mock_enter_credentials, mock_telegram_sink, authenticator, mock_driver
):
    """Test handle_login when element is not found"""
    mock_enter_credentials.side_effect = NoSuchElementException("Element not found")

    result = authenticator.handle_login()

    # Verify
    assert result is False
    mock_driver.get.assert_called_once_with("https://hh.ru")


@patch("src.job_manager.authenticator.Authenticator.is_logged_in")
@patch("src.job_manager.authenticator.Authenticator.handle_login")
def test_start_already_logged_in(mock_handle_login, mock_is_logged_in, authenticator):
    """Test start when user is already logged in"""
    mock_is_logged_in.return_value = True

    result = authenticator.start()

    # Verify
    assert result is True
    mock_is_logged_in.assert_called_once()
    mock_handle_login.assert_not_called()


@patch("src.job_manager.authenticator.Authenticator.is_logged_in")
@patch("src.job_manager.authenticator.Authenticator.handle_login")
def test_start_not_logged_in(mock_handle_login, mock_is_logged_in, authenticator):
    """Test start when user is not logged in"""
    mock_is_logged_in.return_value = False
    mock_handle_login.return_value = True

    result = authenticator.start()

    # Verify
    assert result is True
    mock_is_logged_in.assert_called_once()
    mock_handle_login.assert_called_once()


def test_check_password_is_correct_true(authenticator, mock_driver):
    """Test check_password_is_correct when password is correct"""
    # Mock not finding any error elements
    mock_driver.find_elements.return_value = []

    result = authenticator.check_password_is_correct()

    # Verify
    assert result is True


def test_check_password_is_correct_false(authenticator, mock_driver):
    """Test check_password_is_correct when password is incorrect"""
    # Mock finding an error element
    error_element = MagicMock()
    mock_driver.find_elements.return_value = [error_element]

    result = authenticator.check_password_is_correct()

    # Verify
    assert result is False


@patch("src.job_manager.authenticator.pause")
@patch("src.job_manager.authenticator.Authenticator.process_captcha")
@patch("src.job_manager.authenticator.Authenticator.check_password_is_correct")
def test_enter_credentials_success(
    mock_check_password, mock_process_captcha, mock_pause, authenticator, mock_driver
):
    """Test enter_credentials when successful"""
    # Setup mocks
    login_element = MagicMock()
    login_element.get_attribute.return_value = ""
    mock_driver.find_element.return_value = login_element

    password_switch_button = MagicMock()
    mock_driver.find_elements.return_value = [password_switch_button]

    mock_check_password.return_value = True

    # Call the method
    result = authenticator.enter_credentials()

    # Verify
    assert result is True
    mock_driver.get.assert_called_once_with("https://hh.ru/employer")
    mock_check_password.assert_called_once()


@patch("src.telegram.telegram_error_handler.AsyncTelegramSink.__call__", return_value=None)
@patch("src.job_manager.authenticator.pause")
@patch("src.job_manager.authenticator.Authenticator.process_captcha")
@patch("src.job_manager.authenticator.Authenticator.check_password_is_correct")
def test_enter_credentials_wrong_password(
    mock_check_password,
    mock_process_captcha,
    mock_pause,
    mock_telegram_sink,
    authenticator,
    mock_driver,
):
    """Test enter_credentials when password is incorrect"""
    # Setup mocks
    login_element = MagicMock()
    login_element.get_attribute.return_value = ""
    mock_driver.find_element.return_value = login_element

    password_switch_button = MagicMock()
    mock_driver.find_elements.return_value = [password_switch_button]

    mock_check_password.return_value = False

    # Call the method
    result = authenticator.enter_credentials()

    # Verify
    assert result is False
    mock_check_password.assert_called_once()


@patch("src.telegram.telegram_error_handler.AsyncTelegramSink.__call__", return_value=None)
@patch("src.job_manager.authenticator.load_secrets")
@patch("src.job_manager.authenticator.asyncio.run")
@patch("src.job_manager.authenticator.pause")
@patch("os.path.exists")
@patch("os.remove")
def test_process_captcha_with_captcha(
    mock_remove,
    mock_exists,
    mock_pause,
    mock_asyncio_run,
    mock_load_secrets,
    mock_telegram_sink,
    authenticator,
    mock_driver,
):
    """Test process_captcha when CAPTCHA is present"""
    # Setup
    submit_button = MagicMock()
    captcha_element = MagicMock()
    captcha_element.get_attribute.return_value = "http://example.com/captcha.png"

    # Need to provide enough return values for all possible find_elements calls
    # First for checking captcha, additional for check_password_is_correct, and finally empty list to exit loop
    mock_driver.find_elements.side_effect = [[captcha_element], [], [], []]

    mock_exists.return_value = False
    mock_load_secrets.return_value = ("token", "api_id", "api_hash")
    mock_asyncio_run.return_value = "captcha_answer"

    # Call the method
    authenticator.process_captcha(submit_button)

    # Verify
    assert mock_driver.find_elements.call_count >= 2
    mock_load_secrets.assert_called_once_with(SECRETS_FILE)
    assert mock_asyncio_run.call_count == 1


@patch("src.telegram.telegram_error_handler.AsyncTelegramSink.__call__", return_value=None)
@patch("src.job_manager.authenticator.load_secrets")
@patch("src.job_manager.authenticator.pause")
def test_process_captcha_no_captcha(
    mock_pause, mock_load_secrets, mock_telegram_sink, authenticator, mock_driver
):
    """Test process_captcha when no CAPTCHA is present"""
    # Setup
    submit_button = MagicMock()
    mock_driver.find_elements.return_value = []
    mock_load_secrets.return_value = ("token", "api_id", "api_hash")

    # Call the method
    authenticator.process_captcha(submit_button)

    # Verify
    mock_driver.find_elements.assert_called_once()
    mock_load_secrets.assert_called_once_with(SECRETS_FILE)


def test_set_parameters(authenticator):
    """Test set_parameters method"""
    authenticator.set_parameters(login="new_login", password="new_password")

    assert authenticator.login == "new_login"
    assert authenticator.password == "new_password"
