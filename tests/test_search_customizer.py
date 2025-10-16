from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_api():
    """Fixture to create mock HeadHunterAPI"""
    api_mock = MagicMock()

    # Mock API responses
    areas_response = [
        {
            "name": "Россия",
            "areas": [
                {"name": "Москва", "id": "1", "areas": [{"name": "Центр", "id": "1-1"}]},
                {"name": "Санкт-Петербург", "id": "2", "areas": []},
            ],
        },
        {"name": "Украина", "areas": [{"name": "Киев", "id": "3", "areas": []}]},
    ]

    metro_response = [
        {
            "id": "1",  # Moscow ID
            "lines": [
                {
                    "id": "1",
                    "name": "Сокольническая",
                    "stations": [
                        {"id": "1.1", "name": "Библиотека имени Ленина"},
                        {"id": "1.2", "name": "Парк Культуры"},
                    ],
                }
            ],
        }
    ]

    professional_roles_response = {
        "categories": [
            {
                "id": "1",
                "name": "IT, интернет, телеком",
                "roles": [
                    {"id": "1.1", "name": "Программист, разработчик"},
                    {"id": "1.2", "name": "Data Scientist"},
                ],
            }
        ]
    }

    industries_response = [
        {
            "id": "1",
            "name": "IT, интернет, телеком",
            "industries": [
                {"id": "1.1", "name": "Интернет"},
                {"id": "1.2", "name": "Программное обеспечение"},
            ],
        }
    ]

    # Configure API mock to return different responses based on URL
    def api_request_side_effect(url, *args, **kwargs):
        if url == "https://api.hh.ru/areas":
            return areas_response
        elif url == "https://api.hh.ru/metro":
            return metro_response
        elif url == "https://api.hh.ru/professional_roles":
            return professional_roles_response
        elif url == "https://api.hh.ru/industries":
            return industries_response
        return {}

    api_mock.api_request.side_effect = api_request_side_effect

    return api_mock


@pytest.fixture
def sample_resume():
    """Fixture to create a sample resume"""
    return {"personal_information": {"citizenship": ["Россия"], "legal_authorization": []}}


@pytest.fixture
def search_customizer(mock_api):
    from src.job_manager.search_customizer import SearchCustomizer

    """Fixture to create a SearchCustomizer instance with mocked API"""
    return SearchCustomizer(mock_api)


def test_init(search_customizer):
    """Test that SearchCustomizer initializes correctly"""
    assert search_customizer.resume is None
    assert search_customizer.search_params == {}


def test_set_resume(search_customizer, sample_resume):
    """Test setting resume"""
    search_customizer.set_resume("12345", sample_resume)
    assert search_customizer.resume_id == "12345"
    assert search_customizer.resume == sample_resume


def test_set_advanced_search_params(search_customizer, sample_resume):
    """Test setting advanced search parameters"""
    search_customizer.set_resume("12345", sample_resume)

    # Create parameters to test
    parameters = {
        "keywords": "python developer",
        "search_field": {"name": True, "company_name": False, "description": True},
        "experience": {"noExperience": True, "between1And3": False},
        "employment": {"full": True, "part": False},
        "schedule": {"remote": True, "flexible": False},
        "area": "Москва; Санкт-Петербург",
        "metro": "Библиотека имени Ленина",
        "professional_role": "программист",
        "industry": "интернет,программное обеспечение",
        "salary": 150000,
        "currency": {"RUR": True, "USD": False},
        "vacancy_label": {"with_address": True, "accept_temporary": False},
        "only_with_salary": True,
        "period": {"week": True, "month": False},
        "order_by": {"publication_time": True, "salary_desc": False},
        "part_time": {"project": True, "volunteer": False},
    }

    # Call the method
    search_customizer.set_advanced_search_params(parameters)

    # Check that parameters were set correctly
    assert search_customizer.search_params["text"] == "python developer"
    assert search_customizer.search_params["search_field"] == ["name", "description"]
    assert search_customizer.search_params["experience"] == ["noExperience"]
    assert search_customizer.search_params["employment"] == ["full"]
    assert search_customizer.search_params["schedule"] == ["remote"]
    assert "1" in search_customizer.search_params["area"]  # Moscow ID
    assert "2" in search_customizer.search_params["area"]  # St Petersburg ID
    assert search_customizer.search_params["metro"] == ["1.1"]  # Library ID
    assert search_customizer.search_params["professional_role"] == "1.1"  # Programmer ID
    assert "1.1" in search_customizer.search_params["industry"]  # Internet ID
    assert "1.2" in search_customizer.search_params["industry"]  # Software ID
    assert search_customizer.search_params["salary"] == 150000
    assert search_customizer.search_params["currency"] == "RUR"
    assert search_customizer.search_params["label"] == ["with_address"]
    assert search_customizer.search_params["only_with_salary"] is True
    assert search_customizer.search_params["period"] == 7
    assert search_customizer.search_params["order_by"] == "publication_time"
    assert search_customizer.search_params["part_time"] == ["project"]


def test_get_search_field_ids():
    """Test getting search field IDs"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    parameters = {"search_field": {"name": True, "company_name": False, "description": True}}

    result = customizer._get_search_field_ids(parameters)
    assert result == ["name", "description"]

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_search_field_ids(empty_parameters)
    assert result == []


def test_get_experience_id():
    """Test getting experience ID"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    # Test with a selected experience level
    parameters = {"experience": {"noExperience": False, "between1And3": True}}

    result = customizer._get_experience_id(parameters)
    assert result == ["between1And3"]

    # Test with doesntMatter option
    parameters = {"experience": {"doesntMatter": True, "between1And3": False}}

    result = customizer._get_experience_id(parameters)
    assert result == ""

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_experience_id(empty_parameters)
    assert result == ""


def test_get_employment_ids():
    """Test getting employment IDs"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    parameters = {"employment": {"full": True, "part": False, "project": True}}

    result = customizer._get_employment_ids(parameters)
    assert result == ["full", "project"]

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_employment_ids(empty_parameters)
    assert result == []


def test_get_schedule_ids():
    """Test getting schedule IDs"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    parameters = {"schedule": {"remote": True, "flexible": False}}

    result = customizer._get_schedule_ids(parameters)
    assert result == ["remote"]

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_schedule_ids(empty_parameters)
    assert result == []


def test_get_area_ids(search_customizer, sample_resume):
    """Test getting area IDs"""
    search_customizer.set_resume("12345", sample_resume)

    # Test with valid areas
    result = search_customizer._get_area_ids({"area": "Москва; Санкт-Петербург"})
    assert "1" in result  # Moscow ID
    assert "2" in result  # St Petersburg ID

    # Test with area that doesn't exist in the country
    result = search_customizer._get_area_ids({"area": "Киев"})
    assert len(result) == 0

    # Test with empty parameters
    result = search_customizer._get_area_ids({})
    assert result == []


def test_get_metro_ids(search_customizer, sample_resume):
    """Test getting metro IDs"""
    search_customizer.set_resume("12345", sample_resume)
    search_customizer.search_params["area"] = ["1"]  # Moscow ID

    # Test with valid metro station
    result = search_customizer._get_metro_ids({"metro": "Библиотека имени Ленина"})
    assert result == ["1.1"]  # Library ID

    # Test with metro station that doesn't exist
    result = search_customizer._get_metro_ids({"metro": "Несуществующая"})
    assert result == []

    # Test with empty parameters
    result = search_customizer._get_metro_ids({})
    assert result == []


def test_get_professional_role_id(search_customizer):
    """Test getting professional role ID"""
    # Test with valid role
    result = search_customizer._get_professional_role_id({"professional_role": "программист"})
    assert result == "1.1"  # Programmer ID

    # Test with empty parameters
    result = search_customizer._get_professional_role_id({})
    assert result == ""


def test_get_industry_ids(search_customizer):
    """Test getting industry IDs"""
    # Test with valid industries
    result = search_customizer._get_industry_ids({"industry": "интернет,программное обеспечение"})
    assert set(result) == {"1.1", "1.2"}

    # Test with industry that doesn't exist
    result = search_customizer._get_industry_ids({"industry": "несуществующая"})
    assert result == []

    # Test with empty parameters
    result = search_customizer._get_industry_ids({})
    assert result == []


def test_get_currency_id():
    """Test getting currency ID"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    parameters = {"currency": {"RUR": True, "USD": False}}

    result = customizer._get_currency_id(parameters)
    assert result == "RUR"

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_currency_id(empty_parameters)
    assert result == ""


def test_get_vacancy_label_ids():
    """Test getting vacancy label IDs"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    parameters = {"vacancy_label": {"with_address": True, "accept_temporary": False}}

    result = customizer._get_vacancy_label_ids(parameters)
    assert result == ["with_address"]

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_vacancy_label_ids(empty_parameters)
    assert result == []


def test_get_period():
    """Test getting search period"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    # Test different period options
    assert customizer._get_period({"period": {"all_time": True}}) == 0
    assert customizer._get_period({"period": {"month": True}}) == 30
    assert customizer._get_period({"period": {"week": True}}) == 7
    assert customizer._get_period({"period": {"three_days": True}}) == 3
    assert customizer._get_period({"period": {"one_day": True}}) == 1

    # Test with empty parameters
    assert customizer._get_period({}) == 0


def test_get_order_by_id():
    """Test getting order by ID"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    parameters = {"order_by": {"publication_time": True, "salary_desc": False}}

    result = customizer._get_order_by_id(parameters)
    assert result == "publication_time"

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_order_by_id(empty_parameters)
    assert result is None


def test_get_part_time_ids():
    """Test getting part-time IDs"""
    from src.job_manager.search_customizer import SearchCustomizer

    api_mock = MagicMock()
    customizer = SearchCustomizer(api_mock)

    parameters = {"part_time": {"project": True, "volunteer": False}}

    result = customizer._get_part_time_ids(parameters)
    assert result == ["project"]

    # Test with empty parameters
    empty_parameters = {}
    result = customizer._get_part_time_ids(empty_parameters)
    assert result == []
