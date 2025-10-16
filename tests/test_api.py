from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def api_parameters():
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "user_id": "test_user",
    }


@pytest.fixture
def hh_api(api_parameters):
    from src.job_manager.api import HeadHunterAPI

    with patch("src.job_manager.api.load_yaml_file"), patch.object(HeadHunterAPI, "_get_user_id"):
        api = HeadHunterAPI(api_parameters)
        return api


def test_init_with_user_id(api_parameters):
    from src.job_manager.api import HeadHunterAPI

    api_parameters["user_id"] = "test_user_id"
    with patch("src.job_manager.api.load_yaml_file"):
        api = HeadHunterAPI(api_parameters)
        assert api.access_token == "test_access_token"
        assert api.refresh_token == "test_refresh_token"


@patch("requests.get")
def test_api_request_success(mock_get, hh_api):
    mock_response = Mock()
    mock_response.json.return_value = {"result": "success"}
    mock_get.return_value = mock_response

    response = hh_api.api_request("https://api.hh.ru/test")
    assert response == {"result": "success"}
    mock_get.assert_called_once()


@patch("requests.get")
def test_api_request_error(mock_get, hh_api):
    mock_response = Mock()
    mock_response.json.return_value = {
        "error": "test_error",
        "error_description": "test description",
    }
    mock_get.return_value = mock_response

    with pytest.raises(
        ValueError,
        match="Неизвестная ошибка во время доступа к API HH: test description",
    ):
        hh_api.api_request("https://api.hh.ru/test")


@patch("requests.post")
def test_refresh_token_success(mock_post, hh_api):
    mock_response = Mock()
    mock_response.json.return_value = {
        "access_token": "new_access_token",
        "refresh_token": "new_refresh_token",
    }
    mock_post.return_value = mock_response

    with (
        patch(
            "src.job_manager.api.load_yaml_file",
            return_value={"user_id": "test_user", "tg_token": "test_token"},
        ),
        patch("src.job_manager.api.save_yaml_file"),
    ):
        hh_api.refress_access_token()

        assert hh_api.access_token == "new_access_token"
        assert hh_api.refresh_token == "new_refresh_token"
        assert hh_api.secrets["access_token"] == "new_access_token"
        assert hh_api.secrets["refresh_token"] == "new_refresh_token"


@patch("requests.post")
def test_refresh_token_error(mock_post, hh_api):
    mock_response = Mock()
    mock_response.json.return_value = {"errors": ["test_error"]}
    mock_post.return_value = mock_response

    with pytest.raises(ValueError, match="Ошибки во время обновления токена:"):
        hh_api.refress_access_token()


@patch("requests.get")
def test_get_user_id(mock_get, hh_api):
    mock_response = Mock()
    mock_response.json.return_value = {"id": "test_user_id"}
    mock_get.return_value = mock_response

    with (
        patch(
            "src.job_manager.api.load_yaml_file",
            return_value={"user_id": "test_user", "tg_token": "test_token"},
        ),
        patch("src.job_manager.api.save_yaml_file"),
    ):
        hh_api._get_user_id()
        assert hh_api.secrets["user_id"] == "test_user_id"
