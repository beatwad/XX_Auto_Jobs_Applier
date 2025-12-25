from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def sample_resume():
    """Fixture to create a sample resume"""
    return {"personal_information": {"citizenship": ["Россия"], "legal_authorization": []}}


@pytest.fixture
def manager():
    m = MagicMock()
    m.start_search = AsyncMock()
    m.set_advanced_search_params = AsyncMock()
    return m


@pytest.fixture
def search_customizer(manager):
    from src.job_manager.search_customizer import SearchCustomizer

    """Fixture to create a SearchCustomizer instance with mocked Playwright manager"""
    return SearchCustomizer(manager)


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
        "job_format": {"remote": True, "flexible": False},
        "area": "Москва; Санкт-Петербург",
        "professional_role": "программист",
        "industry": "интернет,программное обеспечение",
        "salary": 150000,
        "currency": {"RUR": True, "USD": False},
        "vacancy_label": {"with_address": True, "accept_temporary": False},
        "only_with_salary": True,
        "period": {"week": True, "month": False},
        "order_by": {"publication_time": True, "salary_desc": False},
    }

    # Call the method (should store raw config as-is; UI setup is done by Playwright manager)
    search_customizer.set_advanced_search_params(parameters)

    assert search_customizer.search_params == parameters


@pytest.mark.asyncio
async def test_start_search_calls_manager(search_customizer, manager, sample_resume):
    search_customizer.set_resume("abc123", sample_resume)
    params = {"keywords": "python"}
    search_customizer.set_advanced_search_params(params)

    await search_customizer.start_search()

    manager.start_search.assert_awaited_once_with("abc123")
    manager.set_advanced_search_params.assert_awaited_once_with(params)
