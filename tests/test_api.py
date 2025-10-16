from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def api_parameters():
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
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
        patch("src.job_manager.api.load_yaml_file"),
        patch("src.job_manager.api.update_search_config_s3"),
    ):
        hh_api.refress_access_token()

        assert hh_api.access_token == "new_access_token"
        assert hh_api.refresh_token == "new_refresh_token"
        assert hh_api.parameters["access_token"] == "new_access_token"
        assert hh_api.parameters["refresh_token"] == "new_refresh_token"


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
        patch("src.job_manager.api.load_yaml_file"),
        patch("src.job_manager.api.update_search_config_s3"),
    ):
        hh_api._get_user_id()
        assert hh_api.parameters["user_id"] == "test_user_id"


def test_remove_secret_info_from_parameters(hh_api):
    hh_api.parameters = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "user_id": "test_user_id",
        "s3_bucket_name": "test_bucket",
        "s3_access_key": "test_access_key",
        "s3_secret_key": "test_secret_key",
    }

    cleaned_parameters = hh_api._remove_secret_info_from_parameters()
    assert "s3_access_key" not in cleaned_parameters
    assert "s3_secret_key" not in cleaned_parameters
    assert "s3_bucket_name" not in cleaned_parameters
