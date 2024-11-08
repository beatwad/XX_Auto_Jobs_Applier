import pytest
from unittest.mock import Mock, MagicMock, patch
from src.llm.llm_manager import AIAdapter, LLMLogger, LoggerChatModel, GPTAnswerer

@pytest.fixture
def mock_config():
    return {
        "llm_api_url": "",
        "model_type": "openai",
        }

@pytest.fixture
def mock_api_key():
    return "test_api_key"

@pytest.fixture
@patch("src.llm.llm_manager.OpenAIModel")
@patch("loguru.logger")
def mock_ai_adapter(openai_model, logger, mock_config, mock_api_key):
    adapter = AIAdapter(mock_config, mock_api_key)
    return adapter

@pytest.fixture
def mock_llm_logger(mock_ai_adapter):
    return LoggerChatModel(mock_ai_adapter)

@pytest.fixture
def gpt_answerer(mock_ai_adapter, mock_llm_logger, mock_config, mock_api_key):
    return GPTAnswerer(mock_config, mock_api_key)

def test_ai_adapter_creation(mock_config, mock_api_key):
    adapter = AIAdapter(mock_config, mock_api_key)
    assert adapter.model is not None

@patch("loguru.logger")
def test_llm_logger_initialization(mock_logger, mock_ai_adapter):
    llm_logger = LLMLogger(mock_ai_adapter)
    assert llm_logger.llm == mock_ai_adapter

@patch("src.llm.llm_manager.LLMLogger.log_request")
def test_logger_chat_model_call(mock_log_request, mock_ai_adapter):
    chat_model = LoggerChatModel(mock_ai_adapter)
    messages = [{"content": "test message", "role": "user"}]
    mock_ai_adapter.model.invoke.return_value = MagicMock(
        content="test_content", 
        id="test_id",
        response_metadata={},
        usage_metadata={},
        )
    
    result = chat_model(messages)
    
    mock_ai_adapter.model.invoke.assert_called_once_with(messages)
    assert result.content == "test_content"

def test_gpt_answerer_initialization(gpt_answerer):
    assert gpt_answerer.ai_adapter is not None
    assert isinstance(gpt_answerer.llm_cheap, LoggerChatModel)

@patch("src.llm.llm_manager.GPTAnswerer.answer_question_textual_wide_range")
def test_gpt_answerer_question_answering(mock_answer, gpt_answerer):
    question = "What is your availability?"
    mock_answer.return_value = "I am available to start immediately."
    
    result = gpt_answerer.answer_question_textual_wide_range(question)
    
    mock_answer.assert_called_once_with(question)
    assert result == "I am available to start immediately."

def test_job_is_interesting_yes(gpt_answerer):
    # Mock the output of the job_is_interesting chain to return "yes"
    gpt_answerer.resume = {"skills": ["Python", "Machine Learning"], "interests": ["AI Research"]}
    gpt_answerer.job = {"description": "Looking for a Python developer interested in AI"}

    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Score: 10. Reasoning: test"
    gpt_answerer.chains["job_is_interesting"] = mock_chain

    # Call the method
    result = gpt_answerer.job_is_interesting()

    # Assert the output is True
    assert result is True
    mock_chain.invoke.assert_called_once_with({
        "resume": gpt_answerer.resume,
        "job_description": gpt_answerer.job_description,
        "skills": gpt_answerer.resume["skills"],
        "interests": gpt_answerer.resume["interests"]
    })

def test_job_is_interesting_no(gpt_answerer):
    # Mock the output of the job_is_interesting chain to return "no"
    gpt_answerer.resume = {"skills": ["Python", "Data Analysis"], "interests": ["Data Science"]}
    gpt_answerer.job = {"description": "Looking for a C++ developer with interest in embedded systems"}

    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Score: 1. Reasoning: test"
    gpt_answerer.chains["job_is_interesting"] = mock_chain

    # Call the method
    result = gpt_answerer.job_is_interesting()

    # Assert the output is False
    assert result is False
    mock_chain.invoke.assert_called_once_with({
        "resume": gpt_answerer.resume,
        "job_description": gpt_answerer.job_description,
        "skills": gpt_answerer.resume["skills"],
        "interests": gpt_answerer.resume["interests"]
    })

def test_find_best_match(gpt_answerer):
    text = "Horse"
    options = ["Home", "Hound", "House", "Hill"]

    result = gpt_answerer.find_best_match(text, options)
    assert result == "House"


@patch("src.llm.llm_manager.StrOutputParser")
@patch("src.llm.llm_manager.ChatPromptTemplate.from_template")
@patch("src.llm.llm_manager.GPTAnswerer.find_best_match", return_value="House")
def test_select_one_answer_from_options(mock_str_output_parser, mock_chat_prompt_template, mock_best_match, gpt_answerer):
    gpt_answerer.resume = Mock()
    gpt_answerer.llm_cheap = Mock()

    question = "Test"
    options = ["Home", "Hound", "House", "Hill"]

    assert gpt_answerer.select_one_answer_from_options(question, options) == options[2]
