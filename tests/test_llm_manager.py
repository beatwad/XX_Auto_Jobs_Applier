from unittest.mock import MagicMock, patch

from src.views.llm import JobIsInteresting

import httpx
import pytest
from langchain_core.messages.ai import AIMessage
from langchain_core.prompts import ChatPromptTemplate


@pytest.fixture
def mock_api_key():
    return "mock_api_key"


@pytest.fixture
def mock_llm_proxy():
    return ["http://proxy1.example.com", "http://proxy2.example.com"]


@pytest.fixture
def mock_config():
    return {"model_config": "test_config"}


@pytest.fixture
def mock_resume():
    return {
        "personal_information": {
            "first_name": "John",
            "last_name": "Doe",
            "sex": "male",
            "preferred_contact": "email",
            "email": "john@example.com",
        },
        "experience_details": {"experience": "5 years as Python Developer"},
        "education_details": {"education": "Computer Science Degree"},
        "skills": ["Python", "Django", "SQL"],
        "salary_expectations": {"amount": 100000, "currency": "RUR"},
        "about_me": "Experienced developer",
        "certifications": ["AWS Certified"],
        "languages": ["English", "Russian"],
    }


@pytest.fixture
def mock_readable_resume():
    return "Test resume"


@pytest.fixture
def mock_search_parameters():
    return {"job_title": "Test"}


@pytest.fixture
def mock_job():
    return {"job_description": "Looking for a Python developer with 3+ years of experience"}


class TestGeminiModel:
    @patch("src.llm.llm_manager.ChatGoogleGenerativeAI")
    def test_init(self, mock_chat_gemini, mock_api_key, mock_llm_proxy):
        from src.llm.llm_manager import GeminiModel

        model = GeminiModel(mock_api_key, "gemini-test-model", mock_llm_proxy)

        assert model.google_api_key == mock_api_key
        assert model.model == "gemini-test-model"
        assert model.llm_proxy == mock_llm_proxy

    @patch("src.llm.llm_manager.ChatGoogleGenerativeAI")
    @patch("src.llm.llm_manager.os")
    def test_invoke_success(self, mock_os, mock_chat_gemini, mock_api_key, mock_llm_proxy):
        # Setup mock
        from src.llm.llm_manager import GeminiModel

        mock_model_instance = MagicMock()
        mock_model_instance.invoke.return_value = AIMessage(content="Test response")
        mock_chat_gemini.return_value = mock_model_instance

        prompt = ChatPromptTemplate.from_template("Test prompt")

        model = GeminiModel(mock_api_key, "gemini-test-model", mock_llm_proxy)
        response = model.invoke(prompt)

        # Verify
        try:
            mock_os.environ.__setitem__.assert_called_with("https_proxy", mock_llm_proxy[0])
        except AssertionError:
            mock_os.environ.__setitem__.assert_called_with("https_proxy", mock_llm_proxy[1])
        mock_chat_gemini.assert_called_once()
        mock_model_instance.invoke.assert_called_once()
        assert response.content == "Test response"
        mock_os.environ.__delitem__.assert_called_with("https_proxy")

    @patch("src.llm.llm_manager.ChatGoogleGenerativeAI")
    @patch("src.llm.llm_manager.os")
    def test_invoke_exception_handling(
        self, mock_os, mock_chat_gemini, mock_api_key, mock_llm_proxy
    ):
        # Setup mock to raise exception on first proxy, succeed on second
        from src.llm.llm_manager import GeminiModel

        mock_model_instance1 = MagicMock()
        mock_model_instance1.invoke.side_effect = Exception("API Error")

        mock_model_instance2 = MagicMock()
        mock_model_instance2.invoke.return_value = AIMessage(content="Success response")

        mock_chat_gemini.side_effect = [mock_model_instance1, mock_model_instance2]

        prompt = ChatPromptTemplate.from_template("Test prompt")

        model = GeminiModel(mock_api_key, "gemini-test-model", mock_llm_proxy)

        with patch("src.llm.llm_manager.time.sleep") as mock_sleep:
            response = model.invoke(prompt)

        # Verify fallback to second proxy
        assert mock_os.environ.__setitem__.call_count == 2
        assert mock_chat_gemini.call_count == 2
        assert mock_sleep.called
        assert response.content == "Success response"


class TestAIAdapter:
    @patch("src.llm.llm_manager.GeminiModel")
    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "gemini")
    @patch("src.llm.llm_manager.LLM_MODEL", "gemini-test-model")
    def test_create_gemini_model(
        self, mock_gemini_model, mock_config, mock_api_key, mock_llm_proxy
    ):
        from src.llm.llm_manager import AIAdapter

        adapter = AIAdapter(mock_api_key, mock_llm_proxy)

        mock_gemini_model.assert_called_once_with(mock_api_key, "gemini-test-model", mock_llm_proxy)
        assert adapter.model == mock_gemini_model.return_value

    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "unsupported")
    @patch("src.llm.llm_manager.LLM_MODEL", "unsupported-model")
    def test_unsupported_model_type(self, mock_config, mock_api_key, mock_llm_proxy):
        from src.llm.llm_manager import AIAdapter

        with pytest.raises(ValueError, match="Неподдерживаемый тип модели: unsupported"):
            AIAdapter(mock_api_key, mock_llm_proxy)

    def test_invoke(self, mock_config, mock_api_key, mock_llm_proxy):
        from src.llm.llm_manager import AIAdapter

        with patch.object(AIAdapter, "_create_model") as mock_create_model:
            mock_model = MagicMock()
            mock_create_model.return_value = mock_model

            adapter = AIAdapter(mock_api_key, mock_llm_proxy)
            adapter.invoke("test prompt")

            mock_model.invoke.assert_called_once_with("test prompt")


class TestLoggerChatModel:
    def test_init(self):
        from src.llm.llm_manager import LoggerChatModel

        mock_llm = MagicMock()
        logger_model = LoggerChatModel(mock_llm)
        assert logger_model.llm == mock_llm

    @patch("src.llm.llm_manager.LLMLogger.log_request")
    def test_call_success(self, mock_log_request, mock_config, mock_api_key, mock_llm_proxy):
        # Setup
        from src.llm.llm_manager import LoggerChatModel

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Test response")

        logger_model = LoggerChatModel(mock_llm)

        messages = [{"role": "user", "content": "Hello"}]

        # Call
        response = logger_model(messages)

        # Verify
        mock_llm.invoke.assert_called_once_with(messages)
        mock_log_request.assert_called_once()
        assert response.content == "Test response"

    @patch("src.llm.llm_manager.time.sleep")
    def test_call_with_retry(self, mock_sleep, mock_config, mock_api_key, mock_llm_proxy):
        # Setup mock to fail with 429 then succeed
        from src.llm.llm_manager import LoggerChatModel

        mock_llm = MagicMock()

        # Create HTTPStatusError with 429 and retry headers
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"retry-after": "1"}

        http_error = httpx.HTTPStatusError(
            "Rate limit exceeded", request=MagicMock(), response=mock_response
        )

        # First call raises error, second succeeds
        mock_llm.invoke.side_effect = [http_error, AIMessage(content="Success after retry")]

        logger_model = LoggerChatModel(mock_llm)

        messages = [{"role": "user", "content": "Hello"}]

        # Call
        with patch("src.llm.llm_manager.LLMLogger.log_request"):
            response = logger_model(messages)

        # Verify
        assert mock_llm.invoke.call_count == 2
        mock_sleep.assert_called_once_with(1)  # Should sleep for 1 second
        assert response.content == "Success after retry"

    def test_parse_llmresult(self):
        from src.llm.llm_manager import LoggerChatModel

        mock_llm = MagicMock()
        logger_model = LoggerChatModel(mock_llm)

        # Test parsing AIMessage with usage_metadata
        ai_message = AIMessage(
            content="Test content",
            response_metadata={
                "model_name": "test-model",
                "system_fingerprint": "test-fingerprint",
                "finish_reason": "stop",
                "logprobs": None,
            },
            id="test-id",
            usage_metadata={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )

        result = logger_model.parse_llmresult(ai_message)

        assert result["content"] == "Test content"
        assert result["response_metadata"]["model_name"] == "test-model"
        assert result["usage_metadata"]["input_tokens"] == 10
        assert result["usage_metadata"]["output_tokens"] == 20
        assert result["usage_metadata"]["total_tokens"] == 30


class TestGPTAnswerer:
    @patch("src.llm.llm_manager.AIAdapter")
    def test_init(self, mock_ai_adapter, mock_config, mock_api_key, mock_llm_proxy):
        from src.llm.llm_manager import GPTAnswerer

        mock_ai_adapter.return_value.llm = MagicMock()

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)

        mock_ai_adapter.assert_called_once_with(mock_api_key, mock_llm_proxy)
        assert answerer.ai_adapter == mock_ai_adapter.return_value
        assert len(answerer.chains) > 0  # Should have created chains

    @patch("src.llm.llm_manager.AIAdapter")
    def test_set_resume(
        self, mock_ai_adapter, mock_resume, mock_config, mock_api_key, mock_llm_proxy
    ):
        mock_ai_adapter.return_value.llm = MagicMock()
        from src.llm.llm_manager import GPTAnswerer

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.set_resume(mock_resume, mock_readable_resume)

        assert answerer.resume == mock_resume
        assert answerer.resume_readable == mock_readable_resume

        # Test currency conversion
        resume_with_rur = {"salary_expectations": {"currency": "RUR"}}
        answerer.set_resume(resume_with_rur, mock_readable_resume)
        assert answerer.resume["salary_expectations"]["currency"] == "руб"

    @patch("src.llm.llm_manager.AIAdapter")
    def test_set_job(self, mock_ai_adapter, mock_job, mock_config, mock_api_key, mock_llm_proxy):
        mock_ai_adapter.return_value.llm = MagicMock()
        from src.llm.llm_manager import GPTAnswerer

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.set_job(mock_job)

        assert answerer.job_description == mock_job

    @patch("src.llm.llm_manager.AIAdapter")
    def test_answer_question_textual_wide_range(
        self,
        mock_ai_adapter,
        mock_resume,
        mock_config,
        mock_api_key,
        mock_llm_proxy,
        mock_readable_resume,
    ):
        from src.llm.llm_manager import GPTAnswerer

        # Setup
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Test answer"

        mock_create_chain = MagicMock(return_value=mock_chain)

        with patch.object(GPTAnswerer, "_create_chain", mock_create_chain):
            answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
            answerer.set_resume(mock_resume, mock_readable_resume)

            result = answerer.answer_question_textual_wide_range("What is your experience?")

            assert result == "Test answer"
            mock_chain.invoke.assert_called_once()
            # Verify invoke is called with the right parameters by checking kwargs directly
            call_kwargs = mock_chain.invoke.call_args[0][0]  # Get the first positional argument
            assert "resume" in call_kwargs
            assert "question" in call_kwargs
            assert call_kwargs["question"] == "What is your experience?"
            assert call_kwargs["resume"] == mock_readable_resume
            assert "sex" in call_kwargs
            assert call_kwargs["sex"] == "male"

    @patch("src.llm.llm_manager.AIAdapter")
    def test_write_cover_letter(
        self, mock_ai_adapter, mock_resume, mock_job, mock_config, mock_api_key, mock_llm_proxy
    ):
        from src.llm.llm_manager import GPTAnswerer

        # Setup
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Test cover letter"

        mock_create_chain = MagicMock(return_value=mock_chain)

        with patch.object(GPTAnswerer, "_create_chain", mock_create_chain):
            answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
            answerer.set_resume(mock_resume, mock_readable_resume)
            answerer.set_job(mock_job)

            result = answerer.write_cover_letter()

            assert result == "Test cover letter"
            mock_chain.invoke.assert_called_once()

    @patch("src.llm.llm_manager.AIAdapter")
    def test_job_is_interesting(
        self,
        mock_ai_adapter,
        mock_resume,
        mock_job,
        mock_config,
        mock_api_key,
        mock_llm_proxy,
    ):
        from src.llm.llm_manager import GPTAnswerer

        # Setup
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = JobIsInteresting(score=71, reasoning="Good match")

        mock_create_pydantic_chain = MagicMock(return_value=(mock_chain, MagicMock()))

        with patch.object(GPTAnswerer, "_create_pydantic_chain", mock_create_pydantic_chain):
            answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
            answerer.set_resume(mock_resume, mock_readable_resume)
            answerer.set_search_parameters(mock_search_parameters)
            answerer.set_job(mock_job)

            result = answerer.job_is_interesting()

            assert result == {"score": 71, "reasoning": "Good match"}
            mock_chain.invoke.assert_called_once()

    @patch("src.llm.llm_manager.AIAdapter")
    def test_job_is_interesting_low_score(
        self, mock_ai_adapter, mock_resume, mock_job, mock_config, mock_api_key, mock_llm_proxy
    ):
        from src.llm.llm_manager import GPTAnswerer

        # Setup
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = JobIsInteresting(score=5, reasoning="Not a good match")

        mock_create_pydantic_chain = MagicMock(return_value=(mock_chain, MagicMock()))

        with patch.object(GPTAnswerer, "_create_pydantic_chain", mock_create_pydantic_chain):
            answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
            answerer.set_resume(mock_resume, mock_readable_resume)
            answerer.set_search_parameters(mock_search_parameters)
            answerer.set_job(mock_job)

            result = answerer.job_is_interesting()

            assert result == {"score": 5, "reasoning": "Not a good match"}
            mock_chain.invoke.assert_called_once()

    @patch("src.llm.llm_manager.AIAdapter")
    def test_find_best_match(self, mock_ai_adapter, mock_config, mock_api_key, mock_llm_proxy):
        from src.llm.llm_manager import GPTAnswerer

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)

        options = ["Red", "Green", "Blue"]

        # Test exact match
        assert answerer.find_best_match("Green", options) == "Green"

        # Test case-insensitive match
        assert answerer.find_best_match("green", options) == "Green"

        # Test closest match with typo
        assert answerer.find_best_match("Gren", options) == "Green"


if __name__ == "__main__":
    pytest.main()
