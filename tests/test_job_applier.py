from datetime import datetime, timedelta
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.api_request.return_value = {"found": 10, "items": ["Test vacancy"]}
    return api


@pytest.fixture
def mock_resume_component():
    resume_component = MagicMock()
    resume_component.job_title = "Software Developer"
    resume_component.deanonymize_personal_information.return_value = "John Doe"
    return resume_component


@pytest.fixture
def mock_search_component():
    search_component = MagicMock()
    search_component.search_params = {
        "area": "1",
        "professional_role": "96",
        "period": "30",
    }
    return search_component


@pytest.fixture
def mock_gpt_answerer():
    gpt_answerer = MagicMock()
    gpt_answerer.write_cover_letter.return_value = "This is a mock cover letter"
    gpt_answerer.job_is_interesting.return_value = True
    gpt_answerer.resume_improvement_recommendations.return_value = "These are mock recommendations"
    gpt_answerer.select_one_answer_from_options.return_value = "Option A"
    gpt_answerer.select_many_answers_from_options.return_value = ["Option A", "Option C"]
    gpt_answerer.answer_question_textual_wide_range.return_value = "This is my answer"
    return gpt_answerer


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    driver.find_elements.return_value = [MagicMock()]
    return driver


@pytest.fixture
def job_applier(mock_api, mock_resume_component, mock_search_component):
    from src.job_manager.job_applier import JobApplier

    applier = JobApplier(mock_api, mock_resume_component, mock_search_component)
    return applier


@pytest.fixture
def job_applier_with_params(job_applier, mock_gpt_answerer):
    parameters = {
        "user_id": "test_user",
        "hh_login": "test_login",
        "hh_password": "test_password",
        "s3_bucket_name": "test_bucket",
        "s3_access_key": "test_access_key",
        "s3_secret_key": "test_secret_key",
        "apply_once_at_company": True,
        "skip_companies_with_test": False,
        "cover_letter": "This is a fixed cover letter",
        "job_blacklist": ["Blacklisted Company"],
        "resume_id": "test_resume_id",
        "resume_titles": ["resume_titles"],
    }

    # Mock methods for loading and saving data
    with (
        patch.object(
            job_applier, "_load_companies_from_yaml", return_value={"Software Developer": {}}
        ),
        patch.object(job_applier, "_load_data_from_yaml", return_value={}),
        patch.object(job_applier, "_load_cache", return_value={}),
    ):
        job_applier.set_parameters(parameters)
        job_applier.set_gpt_answerer(mock_gpt_answerer)
        job_applier.set_resume(
            {"personal_information": {"first_name": "John", "last_name": "Doe"}},
        )
        yield job_applier


def test_job_applier_init(mock_api, mock_resume_component, mock_search_component):
    """Test that JobApplier initializes correctly"""
    from src.job_manager.job_applier import JobApplier

    job_applier = JobApplier(mock_api, mock_resume_component, mock_search_component)
    assert job_applier.api == mock_api
    assert job_applier.resume_component == mock_resume_component
    assert job_applier.search_component == mock_search_component
    assert job_applier.page_num == 0
    assert job_applier.error_num == 0
    assert job_applier.jobs_no_info == []
    assert job_applier.driver is None


def test_set_parameters(job_applier):
    """Test that parameters are set correctly"""
    with (
        patch.object(
            job_applier, "_load_companies_from_yaml", return_value={"Software Developer": {}}
        ),
        patch.object(job_applier, "_load_data_from_yaml", return_value={}),
        patch.object(job_applier, "_load_cache", return_value={}),
    ):
        parameters = {
            "user_id": "test_user",
            "hh_login": "test_login",
            "hh_password": "test_password",
            "s3_bucket_name": "test_bucket",
            "s3_access_key": "test_access_key",
            "s3_secret_key": "test_secret_key",
            "apply_once_at_company": True,
            "skip_companies_with_test": False,
            "cover_letter": "This is a fixed cover letter",
            "job_blacklist": ["Blacklisted Company"],
            "resume_id": "resume_id",
            "resume_titles": ["resume_titles"],
        }

        job_applier.set_parameters(parameters)

        assert job_applier.user_id == "test_user"
        assert job_applier.hh_login == "test_login"
        assert job_applier.hh_password == "test_password"
        assert job_applier.fixed_cover_letter == "This is a fixed cover letter"
        assert job_applier.job_blacklist == ["blacklisted company"]


def test_search_vacancies(job_applier_with_params):
    """Test that search_vacancies method calls the API correctly"""
    job_applier_with_params.search_vacancies(page_num=1)
    job_applier_with_params.api.api_request.assert_called_once_with(
        f"https://api.hh.ru/resumes/{job_applier_with_params.resume_id}/similar_vacancies",
        params={
            "page": 1,
            "per_page": 10,
            "area": "1",
            "professional_role": "96",
            "period": "30",
        },
    )

    job_applier_with_params.search_vacancies(page_num=0)

    job_applier_with_params.api.api_request.call_count == 2
    job_applier_with_params.api.api_request.assert_any_call(
        "https://api.hh.ru/vacancies",
        params={
            "page": 0,
            "per_page": 10,
            "area": "1",
            "professional_role": "96",
            "period": "30",
            "text": "Software Developer",
        },
    )

    with patch.object(
        job_applier_with_params.api, "api_request", return_value=MagicMock()
    ) as mock_api_request:
        mock_api_request.side_effect = [
            {"items": [], "found": 0},
            {"items": ["Main test vacancy"], "found": 1},
        ]
        vacancies = job_applier_with_params.search_vacancies(page_num=1)
        assert vacancies == ["Main test vacancy"]


def test_scrape_vacancy(job_applier_with_params):
    """Test that scrape_vacancy method correctly extracts job information"""
    # Mock the API response for vacancy details
    job_applier_with_params.api.api_request.return_value = {
        "description": "This is a job description",
        "accept_handicapped": True,
        "key_skills": [{"name": "Python"}, {"name": "Django"}],
    }

    # Create a mock vacancy
    vacancy = {
        "id": "123456",
        "name": "Python Developer",
        "area": {"name": "Moscow"},
        "employer": {"name": "Test Company", "id": "654321"},
        "has_test": False,
        "snippet": {"requirement": "Python experience", "responsibility": "Develop web apps"},
        "professional_roles": [{"name": "Developer"}],
    }

    job = job_applier_with_params.scrape_vacancy(vacancy)

    assert job["job_title"] == "Python Developer"
    assert job["vacancy_id"] == vacancy["id"]
    assert job["company_id"] == vacancy["employer"]["id"]
    assert job["area"] == "Moscow"
    assert job["company_name"] == "Test Company"
    assert job["has_test_task"] is False
    assert job["requirement"] == "Python experience"
    assert job["responsibility"] == "Develop web apps"
    assert job["professional_roles"] == ["Developer"]
    assert job["job_description"] == "This is a job description"
    assert job["accept_handicapped_employers"] is True

    # Check that the key skills were extracted
    assert job_applier_with_params.job_key_skills == ["Python", "Django"]

    # Create a mock vacancy
    vacancy = {
        "id": "123456",
        "name": "Python Developer",
        "area": {"name": "Moscow"},
        "employer": {"name": "Test Company"},
        "has_test": False,
        "snippet": {"requirement": "Python experience", "responsibility": "Develop web apps"},
        "professional_roles": [{"name": "Developer"}],
    }

    job = job_applier_with_params.scrape_vacancy(vacancy)

    assert job["company_id"] is None


def test_is_blacklisted(job_applier_with_params):
    """Test that _is_blacklisted method correctly identifies blacklisted companies"""
    assert job_applier_with_params._is_blacklisted("blacklisted company") is True
    assert job_applier_with_params._is_blacklisted("Good Company") is False


def test_is_already_applied_to_job_or_company(job_applier_with_params):
    """Test that _is_already_applied_to_job_or_company correctly identifies already applied jobs"""
    # Mock the API response for vacancy details
    job_applier_with_params.api.api_request.return_value = {
        "description": "This is a job description",
        "accept_handicapped": True,
        "key_skills": [{"name": "Python"}, {"name": "Django"}],
    }

    vacancy = {
        "id": "123456",
        "name": "Python Developer",
        "area": {"name": "Moscow"},
        "employer": {"name": "Test Company", "id": "654321"},
        "has_test": False,
        "snippet": {"requirement": "Python experience", "responsibility": "Develop web apps"},
        "professional_roles": [{"name": "Developer"}],
    }

    job = job_applier_with_params.scrape_vacancy(vacancy)

    # Check if company and vacancy ids are working
    job_applier_with_params.success_companies = {
        "test_resume_id": {"654321": [{"vacancy_id": "123456", "job_title": "Python Developer"}]}
    }

    # When apply_once_at_company is True, should return True for any job at the same company
    is_applied, _ = job_applier_with_params._is_already_applied_to_job_or_company(job)
    assert is_applied is True

    # Check if company and vacnacy names are working
    job_applier_with_params.success_companies = {
        "test_resume_id": {"Test Company": [{"job_title": "Python Developer"}]}
    }

    # When apply_once_at_company is True, should return True for any job at the same company
    is_applied, _ = job_applier_with_params._is_already_applied_to_job_or_company(job)
    assert is_applied is True

    # When apply_once_at_company is False, should only return True for the exact same job
    job_applier_with_params.apply_once_at_company = False

    is_applied, _ = job_applier_with_params._is_already_applied_to_job_or_company(job)
    assert is_applied is True

    # Only if both vacancy_id and job_title are not in the list of seen company - apply the vacancy
    job_applier_with_params.success_companies = {
        "test_resume_id": {
            "654321": [{"vacancy_id": "123456", "job_title": "Python Developer"}],
            "Test Company": [{"job_title": "Python Developer"}],
        }
    }

    job["job_title"] = "New Job"
    is_applied, _ = job_applier_with_params._is_already_applied_to_job_or_company(job)
    assert is_applied is True

    job["vacancy_id"] = "12345"
    is_applied, _ = job_applier_with_params._is_already_applied_to_job_or_company(job)
    assert is_applied is False


def test_sanitize_text(job_applier_with_params):
    """Test that _sanitize_text correctly normalizes text"""
    text = 'TEST Text with "quotes" and \n newlines, \r carriage returns'
    sanitized = job_applier_with_params._sanitize_text(text)

    assert sanitized == "test text with quotes and  newlines,  carriage returns"
    assert sanitized.islower()
    assert '"' not in sanitized
    assert "\n" not in sanitized
    assert "\r" not in sanitized


def test_check_last_search_time(job_applier_with_params):
    """Test that _check_the_last_search_time correctly checks time since last search"""
    # Test when cache is empty
    job_applier_with_params.cache = {}
    assert job_applier_with_params.check_the_last_search_time() is True

    # Test when last run was more than 24 hours ago
    past_time = (datetime.now() - timedelta(hours=25)).isoformat()
    job_applier_with_params.cache = {"last_run": past_time}
    assert job_applier_with_params.check_the_last_search_time() is True

    # Test when last run was less than 24 hours ago
    recent_time = (datetime.now() - timedelta(hours=12)).isoformat()
    job_applier_with_params.cache = {"last_run": recent_time}
    assert job_applier_with_params.check_the_last_search_time() is False

    # Test when last run was less than 24 hours ago but app was rebooted
    recent_time = (datetime.now() - timedelta(hours=12)).isoformat()
    job_applier_with_params.cache = {"last_run": recent_time}
    job_applier_with_params.previous_apply_number = 3
    assert job_applier_with_params.check_the_last_search_time() is True


def test_save_and_load_data(job_applier_with_params):
    """Test that data saving and loading methods work correctly"""
    test_data = {"key": "value"}
    filename = "test_file.yaml"

    # Mock file operations
    with (
        patch("builtins.open", mock_open()) as mock_file,
        patch("yaml.safe_dump") as mock_yaml_dump,
    ):
        job_applier_with_params._save_data_to_yaml(test_data, filename)

        # Check that file operations were called
        mock_file.assert_called_once()
        mock_yaml_dump.assert_called_once()


def test_resume_improvement_recommendations(job_applier_with_params):
    """Test resume_improvement_recommendations method"""
    # Mock _load_data_from_yaml to return empty data (no existing recommendations)
    with (
        patch.object(job_applier_with_params, "_load_data_from_yaml", return_value={}),
        patch.object(job_applier_with_params, "_save_data_to_yaml"),
        patch.object(
            job_applier_with_params.resume_component,
            "deanonymize_personal_information",
            return_value="These are mock recommendations",
        ) as mock_save,
    ):
        job_applier_with_params.resume_improvement_recommendations()

        # Check that GPT answerer was called and recommendations were saved
        job_applier_with_params.gpt_answerer.resume_improvement_recommendations.assert_called_once()
        mock_save.assert_called_once()
        # import code; code.interact(local=dict(globals(), **locals()))
        assert job_applier_with_params.resume_recommendations == "These are mock recommendations"

    # Reset mock for the second part of the test
    job_applier_with_params.gpt_answerer.resume_improvement_recommendations.reset_mock()

    # Test with existing recommendations
    with (
        patch.object(
            job_applier_with_params, "_load_data_from_yaml", return_value="Existing recommendations"
        ),
        patch.object(job_applier_with_params, "_save_data_to_yaml") as mock_save,
    ):
        job_applier_with_params.resume_improvement_recommendations()

        # GPT answerer should not be called when recommendations already exist
        job_applier_with_params.gpt_answerer.resume_improvement_recommendations.assert_not_called()
        mock_save.assert_not_called()


def test_update_skill_stat(job_applier_with_params):
    """Test that _update_skill_stat correctly updates skill statistics"""
    # Mock the _save_data_to_yaml method
    with patch.object(job_applier_with_params, "_save_data_to_yaml") as mock_save:
        # Initialize an empty skill stat dictionary
        job_applier_with_params.skill_stat = {}

        # Test with a list of skills
        skills = ["Python", "Django", "Flask"]
        job_applier_with_params._update_skill_stat(skills)

        # Check that the skill stats were updated
        assert job_applier_with_params.skill_stat == {"Python": 1, "Django": 1, "Flask": 1}
        mock_save.assert_called_once()

        # Reset the mock and test with a skill that contains multiple skills
        mock_save.reset_mock()
        job_applier_with_params._update_skill_stat(["Python; SQL; Git"])

        # Check that each skill was counted separately
        assert job_applier_with_params.skill_stat["Python"] == 2
        assert job_applier_with_params.skill_stat["SQL"] == 1
        assert job_applier_with_params.skill_stat["Git"] == 1
        mock_save.assert_called_once()


def test_process_skill_string(job_applier_with_params):
    """Test that _process_skill_string correctly splits skill strings"""
    skill_string = "Python; SQL; Git; --"
    processed_skills = job_applier_with_params._process_skill_string(skill_string)

    assert processed_skills == ["Python", "SQL", "Git"]

    # Test with extra spaces and special characters
    skill_string = "Python;   SQL (basic);Git!"
    processed_skills = job_applier_with_params._process_skill_string(skill_string)

    assert "Python" in processed_skills
    assert "SQL basic" in processed_skills
    assert "Git" in processed_skills


def test_collect_job_info(job_applier_with_params):
    """Test that _collect_job_info correctly adds job information to the list"""
    job_applier_with_params.jobs_no_info = []

    job_title = "Python Developer"
    job_link = "https://hh.ru/vacancy/123456"
    reason = "Test reason"

    job_applier_with_params._collect_job_info(job_title, job_link, reason)

    assert len(job_applier_with_params.jobs_no_info) == 1
    assert job_applier_with_params.jobs_no_info[0]["job_title"] == job_title
    assert job_applier_with_params.jobs_no_info[0]["link"] == job_link
    assert job_applier_with_params.jobs_no_info[0]["reason"] == reason


def test_handle_radio_question(job_applier_with_params, mock_driver):
    """Test that _handle_radio_question correctly handles radio button questions"""
    # Setup mocks
    job_applier_with_params.driver = mock_driver

    # Create mock question and radio fields
    question = MagicMock()
    question.text = "What is your preferred programming language?"

    radio_fields = [MagicMock(), MagicMock(), MagicMock()]
    for i, field in enumerate(radio_fields):
        parent = MagicMock()
        parent.text = f"Option {chr(65 + i)}"  # "Option A", "Option B", "Option C"
        field.find_element.return_value = parent

    # Test successful answer selection
    with (
        patch("src.job_manager.job_applier.scroll_slow"),
        patch("src.job_manager.job_applier.pause"),
    ):
        success, _ = job_applier_with_params._handle_radio_question(question, radio_fields)

        # Check that the GPT answerer was called with the right parameters
        job_applier_with_params.gpt_answerer.select_one_answer_from_options.assert_called_once_with(
            "What is your preferred programming language?",
            ["Option A", "Option B", "Option C", "No info"],
        )

        # Check that the correct radio button was clicked
        radio_fields[0].click.assert_called_once()
        assert success is True


def test_handle_checkbox_question(job_applier_with_params, mock_driver):
    """Test that _handle_checkbox_question correctly handles checkbox questions"""
    # Setup mocks
    job_applier_with_params.driver = mock_driver

    # Create mock question and checkbox fields
    question = MagicMock()
    question.text = "Which programming languages do you know?"

    checkbox_fields = [MagicMock(), MagicMock(), MagicMock()]
    for i, field in enumerate(checkbox_fields):
        parent = MagicMock()
        parent.text = f"Option {chr(65 + i)}"  # "Option A", "Option B", "Option C"
        field.find_element.return_value = parent

    # Test successful answer selection
    with (
        patch("src.job_manager.job_applier.scroll_slow"),
        patch("src.job_manager.job_applier.pause"),
    ):
        success, _ = job_applier_with_params._handle_checkbox_question(question, checkbox_fields)

        # Check that the GPT answerer was called with the right parameters
        job_applier_with_params.gpt_answerer.select_many_answers_from_options.assert_called_once_with(
            "Which programming languages do you know?",
            ["Option A", "Option B", "Option C", "No info"],
        )

        # Check that the correct checkboxes were clicked
        checkbox_fields[0].click.assert_called_once()
        checkbox_fields[2].click.assert_called_once()
        checkbox_fields[1].click.assert_not_called()
        assert success is True


def test_handle_textbox_question_no_existing_answer(job_applier_with_params, mock_driver):
    """Test that _handle_textbox_question correctly handles textbox questions"""
    # Setup mocks
    job_applier_with_params.driver = mock_driver
    job_applier_with_params.seen_answers = []

    # Create mock question and text field
    question = MagicMock()
    question.text = "Tell us about your experience."
    text_field = MagicMock()

    # Test with no existing answer
    with (
        patch("src.job_manager.job_applier.scroll_slow"),
        patch("src.job_manager.job_applier.pause"),
        patch("src.job_manager.job_applier.enter_text") as mock_enter_text,
        patch.object(job_applier_with_params, "_save_data_to_yaml") as mock_save,
        patch.object(
            job_applier_with_params.resume_component,
            "deanonymize_personal_information",
            return_value="This is my answer",
        ),
    ):
        success, _ = job_applier_with_params._handle_textbox_question(question, text_field)

        # Check that the GPT answerer was called with the right parameters
        job_applier_with_params.gpt_answerer.answer_question_textual_wide_range.assert_called_once_with(
            "Tell us about your experience."
        )

        # Check that the answer was entered in the text field
        mock_enter_text.assert_called_once_with(text_field, "This is my answer")

        # Check that the answer was saved
        assert len(job_applier_with_params.seen_answers) == 1
        assert (
            job_applier_with_params.seen_answers[0]["question"] == "Tell us about your experience."
        )
        assert job_applier_with_params.seen_answers[0]["answer"] == "This is my answer"
        mock_save.assert_called_once()
        assert success is True


def test_handle_textbox_question_with_existing_answer(job_applier_with_params, mock_driver):
    """Test that _handle_textbox_question correctly handles textbox questions"""
    # Setup mocks
    job_applier_with_params.driver = mock_driver
    job_applier_with_params.seen_answers = []

    # Create mock question and text field
    question = MagicMock()
    question.text = "tell us about your experience"
    text_field = MagicMock()

    # Test with existing answer
    job_applier_with_params.seen_answers = [
        {"question": "tell us about your experience", "answer": "existing answer"}
    ]

    with (
        patch("src.job_manager.job_applier.scroll_slow"),
        patch("src.job_manager.job_applier.pause"),
        patch("src.job_manager.job_applier.enter_text") as mock_enter_text,
        patch.object(job_applier_with_params, "_save_data_to_yaml") as mock_save,
        patch.object(
            job_applier_with_params.resume_component,
            "deanonymize_personal_information",
            return_value="existing answer",
        ),
    ):
        success, _ = job_applier_with_params._handle_textbox_question(question, text_field)

        # Check that the GPT answerer was not called (existing answer used)
        job_applier_with_params.gpt_answerer.answer_question_textual_wide_range.call_count == 1

        # Check that the existing answer was entered in the text field
        mock_enter_text.assert_called_once_with(text_field, "existing answer")

        # Check that no new answer was saved
        assert len(job_applier_with_params.seen_answers) == 1
        mock_save.assert_not_called()
        assert success is True


def test_apply_job(job_applier_with_params):
    """Test that apply_job method correctly applies to jobs"""
    # Mock API response for successful application
    job_applier_with_params.api.api_request.return_value = {}

    # Create test data
    vacancy = {
        "id": "123456",
        "alternate_url": "https://hh.ru/vacancy/123456",
        "name": "Python Developer",
    }
    company_name = "Test Company"
    job_title = "Python Developer"
    job = {"title": job_title, "company_name": company_name}

    # Store the original fixed_cover_letter
    original_fixed_cover_letter = job_applier_with_params.fixed_cover_letter

    # Clear fixed_cover_letter to test with mock GPT cover letter
    job_applier_with_params.fixed_cover_letter = None

    # Test successful application
    with (
        patch.object(job_applier_with_params, "_save_cover_letter"),
        patch.object(job_applier_with_params, "_save_company"),
    ):
        result, _ = job_applier_with_params.apply_job(vacancy, company_name, job_title, job)

        assert result == "Success"

    # Restore original fixed_cover_letter
    job_applier_with_params.fixed_cover_letter = original_fixed_cover_letter

    # Test application with API error
    job_applier_with_params.api.api_request.reset_mock()
    job_applier_with_params.api.api_request.return_value = {"errors": [{"value": "limit_exceeded"}]}

    with (
        patch.object(job_applier_with_params, "_save_cover_letter"),
        patch.object(job_applier_with_params, "_save_company"),
        patch("src.job_manager.job_applier.MONKEY_MODE", return_value=False),
        patch("src.job_manager.job_applier.RESUME_MODE", return_value=False),
        patch("src.job_manager.job_applier.SKILL_STAT_MODE", return_value=False),
        patch("src.job_manager.job_applier.SEARCH_MODE", return_value=False),
    ):
        result, _ = job_applier_with_params.apply_job(vacancy, company_name, job_title, job)

        assert result == "Limit"


def test_send_response(job_applier_with_params):
    """Test that send_response method handles job responses correctly"""
    # Mock methods that are called by send_response
    with (
        patch.object(job_applier_with_params, "scrape_vacancy") as mock_scrape,
        patch.object(
            job_applier_with_params, "_is_blacklisted", return_value=False
        ) as mock_blacklist,
        patch.object(
            job_applier_with_params,
            "_is_already_applied_to_job_or_company",
            return_value=(False, ""),
        ) as mock_is_applied,
        patch.object(
            job_applier_with_params, "apply_job", return_value=("Success", "")
        ) as mock_apply,
        patch.object(job_applier_with_params, "_save_company", return_value=None),
        patch.object(job_applier_with_params, "_write_the_last_search_time", return_value=None),
        patch.object(job_applier_with_params, "_update_skill_stat", return_value=None),
        patch("src.job_manager.job_applier.time", return_value=MagicMock()),
        patch("src.job_manager.job_applier.pause"),  #
        patch("src.job_manager.job_applier.sleep"),
        patch("src.job_manager.job_applier.MONKEY_MODE", return_value=False),
        patch("src.job_manager.job_applier.RESUME_MODE", return_value=False),
        patch("src.job_manager.job_applier.SKILL_STAT_MODE", return_value=False),
        patch("src.job_manager.job_applier.SEARCH_MODE", return_value=False),
    ):
        # Setup test data
        vacancy = {
            "id": "123456",
            "name": "Python Developer",
            "alternate_url": "https://hh.ru/vacancy/123456",
            "employer": {"name": "Test Company"},
        }

        mock_scrape.return_value = {
            "job_title": "Python Developer",
            "company_name": "Test Company",
            "has_test_task": False,
            "company_id": "654321",
            "vacancy_id": "123456",
        }

        # Test successful job application
        result = job_applier_with_params.send_repsonse(vacancy)
        # Check that methods were called correctly
        mock_scrape.assert_called_once()
        mock_blacklist.assert_called_once()
        mock_is_applied.assert_called_once()
        job_applier_with_params.gpt_answerer.set_job.assert_called_once()
        job_applier_with_params.gpt_answerer.job_is_interesting.assert_called_once()
        mock_apply.assert_called_once()

        # Check that the success count was incremented
        assert job_applier_with_params.success_applies_num == 1
        assert result == "Success"

    # Test with blacklisted company
    job_applier_with_params.applies_num = 0
    with (
        patch.object(job_applier_with_params, "scrape_vacancy") as mock_scrape,
        patch.object(job_applier_with_params, "_is_blacklisted", return_value=True),
        patch.object(job_applier_with_params, "_save_company") as mock_save_company,
        patch("src.job_manager.job_applier.time.time", return_value=100),
        patch("src.job_manager.job_applier.pause"),
        patch("src.job_manager.job_applier.sleep"),
        patch("src.job_manager.job_applier.MONKEY_MODE", return_value=False),
        patch("src.job_manager.job_applier.RESUME_MODE", return_value=False),
        patch("src.job_manager.job_applier.SKILL_STAT_MODE", return_value=False),
        patch("src.job_manager.job_applier.SEARCH_MODE", return_value=False),
    ):
        vacancy = {
            "id": "123456",
            "name": "Python Developer",
            "alternate_url": "https://hh.ru/vacancy/123456",
            "employer": {"name": "Blacklisted Company"},
        }

        mock_scrape.return_value = {
            "job_title": "Python Developer",
            "company_name": "Blacklisted Company",
            "has_test_task": False,
        }

        result = job_applier_with_params.send_repsonse(vacancy)

        # Company should be saved with Skip status
        mock_save_company.assert_called_once()

        # Check that no success count was incremented
        assert job_applier_with_params.applies_num == 1
        assert job_applier_with_params.success_applies_num == 1  # Unchanged from previous test
        assert result == "Skip"


def test_start_applying(job_applier_with_params):
    """Test that start_applying method correctly manages the job application process"""
    # Mock check_the_last_search_time to return True (valid to search)
    with (
        patch.object(job_applier_with_params, "check_the_last_search_time", return_value=True),
        patch.object(job_applier_with_params, "search_vacancies") as mock_search,
        patch.object(job_applier_with_params, "send_repsonse", return_value="OK") as mock_send,
        patch.object(
            job_applier_with_params, "resume_improvement_recommendations"
        ) as mock_recommendations,
        patch.object(job_applier_with_params, "send_report") as mock_report,
        patch.object(job_applier_with_params, "_write_the_last_search_time") as mock_write_time,
        patch("src.job_manager.job_applier.MONKEY_MODE", return_value=False),
        patch("src.job_manager.job_applier.RESUME_MODE", return_value=False),
        patch("src.job_manager.job_applier.SKILL_STAT_MODE", return_value=False),
        patch("src.job_manager.job_applier.SEARCH_MODE", return_value=False),
    ):
        job_applier_with_params.success_applies_num = 2
        job_applier_with_params.previous_apply_number = 1

        # Mock search results with three vacancies on page 0 and none on page 1
        mock_search.side_effect = [[{"id": f"{i}"} for i in range(3)], []]

        # Start applying to jobs
        job_applier_with_params.start_applying()

        # Check that the search was called twice (for page 0 and page 1)
        assert mock_search.call_count == 2

        # Check that send_response was called for each vacancy
        assert mock_send.call_count == 3

        # Check that other methods were called
        mock_recommendations.assert_called_once()
        mock_report.assert_called_once()

        # If there was a successful application, write_the_last_search_time should be called
        if job_applier_with_params.success_applies_num > 0:
            mock_write_time.assert_called()
