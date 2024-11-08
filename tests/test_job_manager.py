import pytest
from unittest.mock import Mock, patch, MagicMock
from src.job_manager import JobManager
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException


@pytest.fixture
def job_manager():
    driver = MagicMock(current_url = "https://hh.ru/test")  # Mock the webdriver
    _job_manager = JobManager(driver)
    params = {
        "job_title": "test_job",
        "login": "test_login",
        "sort_by": "test",
        "output_period": "test",
        "output_size": "test",
        "experience": "test",
        }
    _job_manager.set_parameters(params)
    _job_manager.gpt_answerer = Mock()
    _job_manager._pause = Mock()
    _job_manager.driver.find_elements.return_value = [MagicMock(location={"y": 0}), MagicMock(location={"y": 0}, text="test_job")]
    _job_manager.driver.find_element.return_value = MagicMock()
    _job_manager.driver.execute_script.return_value = 0
    _job_manager.driver.window_handles = [0, 1, 2]
    _job_manager.wait.until = Mock()
    return _job_manager


def test_start_applying(job_manager):
    job_manager._send_repsonses = Mock()
    job_manager.driver.find_element = Mock(side_effect=[None, NoSuchElementException("No more pages")])  # Simulate pagination
    
    job_manager.start_applying()
    
    assert job_manager._send_repsonses.call_count > 0  # Ensure that responses were sent
    job_manager.driver.find_element.assert_called()


@patch("src.job_manager.DEBUG_MODE", new=False)
def test_apply_job(job_manager):
    job_manager.gpt_answerer.write_cover_letter.return_value = "Sample cover letter"
    job_manager._handle_response_popup = Mock()
    job_manager._find_and_handle_questions = Mock(return_value=(True, ""))
    job_manager._write_and_send_cover_letter = Mock()
    # при первом вызове job_manager.driver.find_elements вернет непустой списко
    # при втором вызове - пустой список
    job_manager.driver.find_elements.side_effect = [[Mock()], []]

    job_manager.apply_job("Test Company", "Test Job")

    job_manager._handle_response_popup.assert_called_once()
    job_manager._write_and_send_cover_letter.assert_called_once_with("Sample cover letter")


def test_send_responses(job_manager):
    job_manager._scrape_employer_page = Mock(return_value={"company_name": "Test Company", "title": "Test Job"})
    job_manager._is_blacklisted = Mock(return_value=False)
    job_manager._is_already_applied_to_job_or_company = Mock(return_value=(False, ""))
    job_manager.apply_job = Mock(return_value=("Success", ""))
    job_manager._save_company_to_json = Mock()
    job_manager._sleep = Mock()

    job_manager._send_repsonses()

    job_manager.apply_job.assert_called()
    job_manager._save_company_to_json.assert_called()


def test_scrape_employer_page(job_manager):
    mock_element = Mock()
    mock_element.text = "Test Data"
    job_manager.driver.find_element.return_value = mock_element
    job_manager.driver.find_elements.return_value = [mock_element]

    job_data = job_manager._scrape_employer_page()

    assert job_data["title"] == "Test Data"
    assert job_data["skills"] == "Test Data"


def test_define_answers_output_file(job_manager):
    output_file = job_manager._define_answers_output_file("test_output.json")
    assert "test_output.json" in str(output_file)

@patch('json.load', return_value={})
def test_save_company(mock_json_load, job_manager):
    job_manager._save_company_to_json = Mock()
    job_manager.succes_companies = {"test_login": {"test_job": {}}}

    company_name = "test_name"
    company_job_title = "test_title"
    apply_result = "Success", "test"

    with patch("builtins.open", MagicMock()):
        job_manager.save_company(company_name, company_job_title, apply_result)
    assert job_manager.succes_companies ==  {'test_login': {'test_job': {'test_name': [{'job_title': 'test_title', 
                                                                                        'link': 'https://hh.ru/test', 
                                                                                        'reason': 'test'}]}}}

@patch("json.dump")
@patch("json.load", return_value={})
def test_save_company_to_json(mock_json_dump, mock_json_load, job_manager):
    job_manager._define_answers_output_file = Mock(return_value="path/to/output.json")
    job_info = [{"name": "company_1", "link": "https://hh.ru/company_1", "reason": ""}]
    
    with patch("builtins.open", MagicMock()):
        job_manager._save_company_to_json("success.json", job_info)

    mock_json_dump.assert_called_once()
    mock_json_load.assert_called_once()


@patch("json.load", return_value={"test_login": {"test_job": {}}})
def test_load_companies_from_json(_, job_manager):
    job_manager._define_answers_output_file = Mock(return_value="path/to/companies.json")

    with patch("builtins.open", MagicMock()):
        data = job_manager._load_companies_from_json("success.json")
    assert data == {"test_login": {"test_job": {}}}


@patch("json.dump")
@patch("json.load", return_value=[{"question": "What is your salary expectations?", "answer": "Test"}])
def test_load_questions_from_json(mock_json_dump, mock_json_load, job_manager):
    job_manager._define_answers_output_file = Mock(return_value="path/to/answers.json")

    with patch("builtins.open", MagicMock()):
        data = job_manager._load_questions_from_json()

    assert data == [{"question": "What is your salary expectations?", "answer": "Test"}]


@patch("json.dump")
def test_save_questions_to_json(mock_json_dump, job_manager):
    job_manager._define_answers_output_file = Mock(return_value="path/to/answers.json")

    with patch("builtins.open", MagicMock()):
        job_manager._save_questions_to_json({"question": "What is your salary expectations?"})

    mock_json_dump.assert_called_once()


def test_handle_response_popup(job_manager):
    job_manager._handle_response_popup()
    job_manager.driver.find_element.assert_called()


def test_find_and_handle_questions(job_manager):
    job_manager._handle_question = Mock(return_value=(True, ""))

    result, _ = job_manager._find_and_handle_questions()

    assert result is True
    job_manager._handle_question.assert_called()


def test_handle_question(job_manager):
    question = MagicMock(spec=WebElement, text="Test Question")
    question.find_elements.return_value = ["test"]
    job_manager._handle_radio_question = Mock(return_value=(True, ""))

    result, _ = job_manager._find_and_handle_questions()

    assert result is True
    job_manager._handle_radio_question.assert_called()


def test_handle_radio_question(job_manager):
    job_manager._scroll_slow = Mock()
    job_manager.gpt_answerer.select_one_answer_from_options.return_value = "Field2"
    question = MagicMock(spec=WebElement, text="Test Question")
    question.find_elements.return_value = ["test"]
    radio_fields = [
        MagicMock(spec=WebElement, text="Field1"),
        MagicMock(spec=WebElement, text="Field2"),
        ]

    result, _ = job_manager._handle_radio_question(question, radio_fields)

    assert result is True
    job_manager.gpt_answerer.select_one_answer_from_options.assert_called()


def test_handle_checkbox_question(job_manager):
    job_manager._scroll_slow = Mock()
    job_manager.gpt_answerer.select_many_answers_from_options.return_value = ["Field2", "Field3"]
    question = MagicMock(spec=WebElement, text="Test Question")
    question.find_elements.return_value = ["test"]
    radio_fields = [
        MagicMock(spec=WebElement, text="Field1"),
        MagicMock(spec=WebElement, text="Field2"),
        ]

    result, _ = job_manager._handle_checkbox_question(question, radio_fields)

    assert result is True
    job_manager.gpt_answerer.select_many_answers_from_options.assert_called()


@patch("builtins.open")
def test_handle_textbox_question(mock_open, job_manager):
    job_manager._scroll_slow = Mock()
    job_manager._enter_text = Mock()
    job_manager.gpt_answerer.answer_question_textual_wide_range.return_value = "Test Answer"
    question = MagicMock(spec=WebElement, text="Test Question")
    question.find_elements.return_value = [Mock()]
    text_field = MagicMock(spec=WebElement, text="Field1")

    result, _ = job_manager._handle_textbox_question(question, text_field)

    assert result is True
    job_manager._enter_text.assert_called()


def test_write_and_send_cover_letter(job_manager):
    job_manager._scroll_slow = Mock()
    job_manager._enter_text = Mock()

    job_manager._write_and_send_cover_letter("Sample Cover Letter")

    job_manager._scroll_slow.assert_called()
    job_manager._enter_text.assert_called_with(job_manager.driver.find_elements.return_value[0], "Sample Cover Letter")


def test_is_blacklisted(job_manager):
    job_manager.job_blacklist = ["Company A"]
    assert job_manager._is_blacklisted("Company A") is True
    assert job_manager._is_blacklisted("Company B") is False

@patch("src.app_config.APPLY_ONCE_AT_COMPANY", new=True)
def test_is_already_applied_to_job_or_company(job_manager):
    job_manager.succes_companies = {"test_user": {"test_job": {"Company A": [{"job_title": "Job 1"}, {"job_title": "Job 2"}]}}}
    job_manager.login = "test_user"
    job_manager.job_title = "test_job"

    result_a = job_manager._is_already_applied_to_job_or_company("company a", "job 1")
    assert result_a[0] is True
    result_b = job_manager._is_already_applied_to_job_or_company("company b", "job 1")
    assert result_b[0] is False


@patch("selenium.webdriver.support.ui.WebDriverWait.until", value=Mock())
def test_enter_advanced_search_menu(_, job_manager):
    job_manager.driver.find_elements.return_value = [MagicMock(text="abc"), MagicMock(text="test_job")]
    job_manager._scroll_slow = Mock()
    job_manager._click_button = Mock()

    with patch("time.sleep"):  # Mock sleep to skip delays
        job_manager._enter_advanced_search_menu()

    job_manager._click_button.assert_called()


def test_sanitize_text(job_manager):
    sanitized = job_manager._sanitize_text(" This is a \ntest! ")
    assert sanitized == "this is a test!"
