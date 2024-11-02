import pytest
from unittest.mock import Mock, patch
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from src.authenticator import Authenticator

@pytest.fixture
def mock_driver():
    """Fixture to create a mock driver for Selenium interactions."""
    return Mock()

def mock_login():
    """Fixture to create a mock driver for Selenium interactions."""
    return Mock()

@pytest.fixture
def authenticator(mock_driver):
    """Fixture to create an instance of the Authenticator class with a mock driver."""
    auth = Authenticator(driver=mock_driver)
    auth.login = "abc"
    return auth

def test_set_parameters(authenticator):
    """Test setting parameters in Authenticator."""
    params = {'login': 'test_user'}
    authenticator.set_parameters(params)
    assert authenticator.login == 'test_user', "Failed to set login parameter"

@patch('src.authenticator.Authenticator.is_logged_in', return_value=True)
def test_start_already_logged_in(mock_is_logged_in, authenticator):
    """Test start method when the user is already logged in."""
    result = authenticator.start()
    assert result is True
    mock_is_logged_in.assert_called_once()

@patch('src.authenticator.Authenticator.is_logged_in', return_value=False)
@patch('src.authenticator.Authenticator.handle_login', return_value=True)
def test_start_login_required(mock_handle_login, mock_is_logged_in, authenticator):
    """Test start method when login is required."""
    result = authenticator.start()
    assert result is True
    mock_is_logged_in.assert_called_once()
    mock_handle_login.assert_called_once()

@patch('src.authenticator.Authenticator.enter_credentials', return_value=True)
def test_handle_login_success(mock_enter_credentials, authenticator):
    """Test handle_login method when login is successful."""
    result = authenticator.handle_login()
    assert result is True
    authenticator.driver.get.assert_called_once_with("https://hh.ru")
    mock_enter_credentials.assert_called_once()

@patch('src.authenticator.Authenticator.enter_credentials', side_effect=NoSuchElementException)
def test_handle_login_failure(mock_enter_credentials, authenticator):
    """Test handle_login method when login fails due to NoSuchElementException."""
    result = authenticator.handle_login()
    assert result is False
    mock_enter_credentials.assert_called_once()

def test_enter_credentials_success(authenticator):
    """Test entering credentials successfully."""
    # Mock elements and their behaviors
    authenticator.driver.find_elements.return_value = ["vacancy"]

    # Call enter_credentials and check interactions
    result = authenticator.enter_credentials()
    assert result is True

    authenticator.driver.find_element.assert_any_call("css selector", '[data-qa="login"]')
    authenticator.driver.find_element.assert_any_call("name", "login")
    authenticator.driver.find_elements.assert_called_with("css selector", '[data-qa="mainmenu_vacancyResponses"]')

@patch('time.sleep', return_value=None)  # To skip delays in tests
def test_enter_credentials_user_not_logged_in(mock_sleep, authenticator):
    """Test enter_credentials method when user is not logged in initially."""
    # Mock login process behavior with delays
    authenticator.driver.find_elements.side_effect = [[], ["vacancy"]]  # First empty, then success

    result = authenticator.enter_credentials()
    assert result is True
    assert mock_sleep.called

def test_is_logged_in_with_logo_and_resume(authenticator):
    """Test is_logged_in method when user is logged in with logo and resume found."""
    mock_logo = Mock()
    mock_resume_element = Mock()
    authenticator.driver.find_elements.side_effect = [[mock_resume_element], []]  # Resume found

    result = authenticator.is_logged_in()
    assert result is True
    authenticator.driver.get.assert_called_once_with("https://www.hh.ru")

def test_is_logged_in_with_logo_and_profile(authenticator):
    """Test is_logged_in method when user is logged in with logo and profile found."""
    mock_logo = Mock()
    mock_profile_element = Mock()
    authenticator.driver.find_elements.side_effect = [[], [mock_profile_element]]  # Profile found

    result = authenticator.is_logged_in()
    assert result is True
    authenticator.driver.get.assert_called_once_with("https://www.hh.ru")

def test_is_logged_in_timeout_exception(authenticator):
    """Test is_logged_in method when a TimeoutException occurs."""
    authenticator.driver.get.side_effect = TimeoutException

    result = authenticator.is_logged_in()
    assert result is False
