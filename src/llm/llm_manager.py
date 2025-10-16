import os
import random
import re
import textwrap
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import httpx
import yaml
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompt_values import StringPromptValue
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from Levenshtein import distance

import src.llm.prompts as prompts
from src.app_config import JOB_IS_INTERESTING_THRESH, LLM_MODEL, LLM_MODEL_TYPE, TEMPERATURE
from src.constants import PRICE_DICT
from src.logger_config import logger
from src.utils.json_to_readable import transform_search_config_data, transform_vacancy_data

load_dotenv()


class AIModel(ABC):
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        pass


# class OpenAIModel(AIModel):
#     """Получить доступ к модели OpenAI"""

#     def __init__(self, api_key: str, llm_model: str, llm_proxy: Union[str, None] = None) -> None:
#         self.llm_proxy = llm_proxy
#         self.model_name = llm_model
#         self.openai_api_key = api_key

#     def invoke(self, prompt: ChatPromptTemplate) -> BaseMessage:
#         logger.info("Получен доступ к модели через OpenAI API")
#         prompt_messages = [SystemMessage(content=prompts.custom_instructions)] + prompt.messages
#         # случайно выбираем одну прокси за другой, пока запрос к LLM не пройдет
#         llm_proxies = self.llm_proxy.copy()
#         random.shuffle(llm_proxies)

#         for proxy in llm_proxies:
#             model = ChatOpenAI(
#                 model_name=self.model_name,
#                 openai_api_key=self.openai_api_key,
#                 openai_proxy=proxy,
#                 temperature=TEMPERATURE,
#                 presence_penalty=0,
#                 frequency_penalty=0,
#                 timeout=60,
#             )
#             try:
#                 response = model.invoke(prompt_messages)
#                 return response
#             except Exception as e:
#                 tb_str = traceback.format_exc()
#                 logger.error(
#                     f"Ошибка доступа к LLM с использованием прокси {proxy.split('@')[-1]}: \n Traceback: {tb_str}"
#                 )
#                 time.sleep(3)


class GeminiModel(AIModel):
    """Получить доступ к модели Gemini"""

    def __init__(self, api_key: str, llm_model: str, llm_proxy: Union[str, None] = None) -> None:
        self.llm_proxy = llm_proxy
        self.model = llm_model
        self.google_api_key = api_key

    def invoke(self, prompt: ChatPromptTemplate) -> BaseMessage:
        logger.info("Получен доступ к модели через Gemini API")
        prompt_messages = [SystemMessage(content=prompts.custom_instructions)] + prompt.messages
        # случайно выбираем одну прокси за другой, пока запрос к LLM не пройдет
        llm_proxies = self.llm_proxy.copy()
        random.shuffle(llm_proxies)

        for proxy in llm_proxies:
            try:
                os.environ["https_proxy"] = proxy
                model = ChatGoogleGenerativeAI(
                    model=self.model,
                    google_api_key=self.google_api_key,
                    temperature=TEMPERATURE,
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DEROGATORY: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_TOXICITY: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_VIOLENCE: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_MEDICAL: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    },
                )
                response = model.invoke(prompt_messages)
                del os.environ["https_proxy"]
                return response
            except Exception:
                tb_str = traceback.format_exc()
                logger.error(
                    f"Ошибка доступа к LLM с использованием прокси {proxy.split('@')[-1]}: \n Traceback: {tb_str}"
                )
                time.sleep(3)
            finally:
                try:
                    del os.environ["https_proxy"]
                except KeyError:
                    pass


# class ClaudeModel(AIModel):
#     """Получить доступ к модели Claude"""

#     def __init__(self, api_key: str, llm_model: str) -> None:
#         from langchain_anthropic import ChatAnthropic

#         self.model = ChatAnthropic(model=llm_model, api_key=api_key, temperature=TEMPERATURE)

#     def invoke(self, prompt: str) -> BaseMessage:
#         response = self.model.invoke(prompt)
#         logger.debug("Успешно получен доступ к модели через Claude API")
#         return response


# class OllamaModel(AIModel):
#     """Получить доступ к модели Ollama"""

#     def __init__(self, llm_model: str, llm_api_url: str) -> None:
#         from langchain_ollama import ChatOllama

#         if len(llm_api_url) > 0:
#             logger.debug(f"Используем Ollama с API URL: {llm_api_url}")
#             self.model = ChatOllama(model=llm_model, base_url=llm_api_url)
#         else:
#             self.model = ChatOllama(model=llm_model)

#     def invoke(self, prompt: str) -> BaseMessage:
#         response = self.model.invoke(prompt)
#         logger.debug("Успешно получен доступ к модели через Ollama API")
#         return response

# class HuggingFaceModel(AIModel):
#     """Получить доступ к модели Hugging Face"""

#     def __init__(self, api_key: str, llm_model: str) -> None:
#         from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

#         self.model = HuggingFaceEndpoint(
#             repo_id=llm_model, huggingfacehub_api_token=api_key, temperature=TEMPERATURE
#         )
#         self.chatmodel = ChatHuggingFace(llm=self.model)

#     def invoke(self, prompt: str) -> BaseMessage:
#         response = self.chatmodel.invoke(prompt)
#         logger.debug("Успешно получен доступ к модели через Hugging Face API")
#         return response


# class GigaChatModel(AIModel):
#     """Получить доступ к модели GigaChat"""

#     def __init__(self, api_key: str, llm_model: str) -> None:
#         from langchain_gigachat import GigaChat

#         if "GIGACHAT_CREDENTIALS" not in os.environ:
#             os.environ["GIGACHAT_CREDENTIALS"] = api_key
#         self.model = GigaChat(
#             verify_ssl_certs=False,
#             scope="GIGACHAT_API_PERS",
#             temperature=TEMPERATURE,
#             model=llm_model,
#         )

#     def invoke(self, prompt: ChatPromptTemplate) -> BaseMessage:
#         logger.info("Получен доступ к модели через GigaChat API")
#         prompt_messages = [SystemMessage(content=prompts.custom_instructions)] + prompt.messages
#         response = self.model.invoke(prompt_messages)
#         return response


class AIAdapter:
    """Класс для получения доступа к LLM моделям разных фирм через API"""

    def __init__(self, api_key: str, llm_proxy: str):
        self.model = self._create_model(api_key, llm_proxy)

    def _create_model(self, api_key: str, llm_proxy: str) -> AIModel:
        logger.info(f"Используем {LLM_MODEL_TYPE} от {LLM_MODEL}")

        if LLM_MODEL_TYPE == "gemini":
            return GeminiModel(api_key, LLM_MODEL, llm_proxy)
        # elif LLM_MODEL_TYPE == "openai":
        #     return OpenAIModel(api_key, LLM_MODEL, llm_proxy)
        # elif LLM_MODEL_TYPE == "gigachat":
        #     return GigaChatModel(api_key, LLM_MODEL)
        # elif LLM_MODEL_TYPE == "claude":
        #     return ClaudeModel(api_key, LLM_MODEL)
        # elif LLM_MODEL_TYPE == "ollama":
        #     return OllamaModel(LLM_MODEL, llm_api_url)
        # elif LLM_MODEL_TYPE == "huggingface":
        #     return HuggingFaceModel(api_key, LLM_MODEL)
        else:
            raise ValueError(f"Неподдерживаемый тип модели: {LLM_MODEL_TYPE}")

    def invoke(self, prompt: str) -> str:
        return self.model.invoke(prompt)


class LLMLogger:
    """Класс для логирования всех событий, происходящих при работе с LLM"""

    def __init__(self, llm: GeminiModel):
        self.llm = llm
        logger.info(f"LLMLogger успешно инициализирован, используем LLM: {llm}")

    @staticmethod
    def log_request(prompts, parsed_reply: Dict[str, Dict]) -> None:
        """Метод для логирования всех операций с LLM"""
        logger.info("Начинается выполнение метода log_request")
        logger.info("Получены промпты")
        logger.info("Получен распарсенный ответ")

        try:
            calls_log = os.path.join(Path("data_folder/output"), "llm_api_calls.yaml")
            logger.debug(f"Определен путь к лог-файлу: {calls_log}")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при определении пути к лог-файлу: {tb_str}")
            raise

        if isinstance(prompts, StringPromptValue):
            logger.debug("Промпты имеют тип StringPromptValue")
            prompts = prompts.text
        elif isinstance(prompts, Dict):
            logger.debug("Промпты имеют тип Dict")
            try:
                prompts = {
                    f"prompt_{i + 1}": prompt.content for i, prompt in enumerate(prompts.messages)
                }
                logger.debug("Промпты преобразованы в словарь")
            except Exception:
                tb_str = traceback.format_exc()
                logger.error(f"Ошибка при преобразовании промптов в словарь: {tb_str}")
                raise
        else:
            logger.debug("Неизвестный тип промптов, попытка преобразования по умолчанию")
            try:
                prompts = {
                    f"prompt_{i + 1}": prompt.content for i, prompt in enumerate(prompts.messages)
                }
                logger.debug("Промпты преобразованы в словарь с использованием метода по умолчанию")
            except Exception:
                tb_str = traceback.format_exc()
                logger.error(
                    f"Ошибка при преобразовании промптов с использованием метода по умолчанию: {tb_str}"
                )
                raise

        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(f"Текущее время: {current_time}")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при получении текущего времени: {tb_str}")
            raise

        try:
            token_usage = parsed_reply["usage_metadata"]
            output_tokens = token_usage["output_tokens"]
            input_tokens = token_usage["input_tokens"]
            total_tokens = token_usage["total_tokens"]
            logger.info(
                f"Использование токенов - Input: {input_tokens}, Output: {output_tokens}, Всего: {total_tokens}"
            )
        except KeyError as e:
            logger.error(f"Ошибка ключа в структуре parsed_reply: {str(e)}")
            raise

        try:
            model_name = parsed_reply["response_metadata"]["model_name"]
            logger.info(f"Название модели: {model_name}")
        except KeyError as e:
            logger.error(f"Ошибка ключа в response_metadata: {str(e)}")
            raise

        try:
            # Рассчитать общую стоимость запроса
            prices = PRICE_DICT.get(
                LLM_MODEL, {"price_per_input_token": 1.5e-7, "price_per_output_token": 6e-7}
            )
            price_per_input_token = prices["price_per_input_token"]
            price_per_output_token = prices["price_per_output_token"]
            total_cost = (input_tokens * price_per_input_token) + (
                output_tokens * price_per_output_token
            )
            logger.info(f"Общая стоимость рассчитана: {total_cost}")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при расчете общей стоимости: {tb_str}")
            raise

        # загружаем лог из лог-файла
        try:
            with open(calls_log, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except FileNotFoundError:
            pass
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при загрузке лога из файла: {tb_str}")
            raise


class LoggerChatModel:
    """
    Класс для взаимодействия с языковой моделью (LLM) и логирования всех операций.
    Этот класс обрабатывает запросы к языковой модели, парсит и логирует ответы, а также обрабатывает
    возможные ошибки, такие как превышение лимита запросов или сетевые ошибки.
    """

    def __init__(self, llm: GeminiModel):
        self.llm = llm
        logger.info(f"LoggerChatModel успешно инициализирован, LLM: {llm}")

    def __call__(self, messages: List[Dict[str, str]]) -> str:
        """
        Выполняем вызов LLM, обрабатываем ответ и логируем весь процесс.
        """
        # logger.debug(f"Вход в метод __call__ с сообщениями: {messages}")
        while True:
            try:
                logger.info("Попытка вызова LLM")

                reply = self.llm.invoke(messages)
                logger.debug(f"Ответ от LLM: {reply}")

                parsed_reply = self.parse_llmresult(reply)
                logger.info(f"Успешно распарсили результат работы LLM: {parsed_reply}")

                LLMLogger.log_request(prompts=messages, parsed_reply=parsed_reply)

                return reply

            except httpx.HTTPStatusError as e:
                logger.error(f"Произошла ошибка HTTPStatusError: {str(e)}")
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("retry-after")
                    retry_after_ms = e.response.headers.get("retry-after-ms")

                    if retry_after:
                        wait_time = int(retry_after)
                        logger.warning(
                            f"Превышен лимит запросов. Ожидание {wait_time} секунд перед повторной попыткой (из заголовка 'retry-after')..."
                        )
                        time.sleep(wait_time)
                    elif retry_after_ms:
                        wait_time = int(retry_after_ms) / 1000.0
                        logger.warning(
                            f"Превышен лимит запросов. Ожидание {wait_time} секунд перед повторной попыткой (из заголовка 'retry-after-ms')..."
                        )
                        time.sleep(wait_time)
                    else:
                        wait_time = 30
                        logger.warning(
                            f"Заголовок 'retry-after' не найден. Ожидание {wait_time} секунд перед повторной попыткой (по умолчанию)..."
                        )
                        time.sleep(wait_time)
                else:
                    logger.error(
                        f"Произошла ошибка HTTP со статусом: {e.response.status_code}, ожидание 30 секунд перед повторной попыткой"
                    )
                    time.sleep(30)

    def parse_llmresult(self, llmresult: AIMessage) -> Dict[str, Dict]:
        """Парсим результат работы LLM"""
        logger.info("Парсинг результата LLM")

        try:
            if hasattr(llmresult, "usage_metadata") and llmresult.usage_metadata is not None:
                content = llmresult.content
                response_metadata = llmresult.response_metadata
                id_ = llmresult.id
                usage_metadata = llmresult.usage_metadata

                parsed_result = {
                    "content": content,
                    "response_metadata": {
                        "model_name": response_metadata.get("model_name", ""),
                        "system_fingerprint": response_metadata.get("system_fingerprint", ""),
                        "finish_reason": response_metadata.get("finish_reason", ""),
                        "logprobs": response_metadata.get("logprobs", None),
                    },
                    "id": id_,
                    "usage_metadata": {
                        "input_tokens": usage_metadata.get("input_tokens", 0),
                        "output_tokens": usage_metadata.get("output_tokens", 0),
                        "total_tokens": usage_metadata.get("total_tokens", 0),
                    },
                }
            else:
                try:
                    content = llmresult.content
                    response_metadata = llmresult.response_metadata
                    id_ = llmresult.id

                    # Handle the case where token_usage might not be in response_metadata
                    if "token_usage" in response_metadata:
                        token_usage = response_metadata["token_usage"]
                        input_tokens = token_usage.prompt_tokens
                        output_tokens = token_usage.completion_tokens
                        total_tokens = token_usage.total_tokens
                    else:
                        # Default values when token_usage is not available
                        input_tokens = 0
                        output_tokens = 0
                        total_tokens = 0

                    parsed_result = {
                        "content": content,
                        "response_metadata": {
                            "model_name": response_metadata.get("model", ""),
                            "finish_reason": response_metadata.get("finish_reason", ""),
                        },
                        "id": id_,
                        "usage_metadata": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": total_tokens,
                        },
                    }
                except Exception:
                    tb_str = traceback.format_exc()
                    logger.error(f"Ошибка при обработке результата без usage_metadata: {tb_str}")
                    # Create a minimal parsed result with defaults
                    parsed_result = {
                        "content": llmresult.content if hasattr(llmresult, "content") else "",
                        "response_metadata": {"model_name": "unknown", "finish_reason": "unknown"},
                        "id": llmresult.id if hasattr(llmresult, "id") else "",
                        "usage_metadata": {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                        },
                    }
            return parsed_result

        except KeyError as e:
            logger.error(f"Ошибка KeyError при парсинге результата LLM: отсутствует ключ {str(e)}")
            raise

        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Непредвиденная ошибка при парсинге результата LLM: {tb_str}")
            raise


class GPTAnswerer:
    """
    Класс для обработки вопросов по резюме и формированию ответов на них с использованием LLM.
    Класс включает методы для обработки и определения разделов резюме, таких как
    личная информация, опыт работы и прочее, на основе переданных вопросов.
    Предназначен для автоматизации ответов на вопросы по резюме,
    а также написания сопроводительных писем.
    """

    def __init__(self, llm_api_key: str, llm_proxy: str):
        self.job = None
        self.ai_adapter = AIAdapter(llm_api_key, llm_proxy)
        self.llm_cheap = LoggerChatModel(self.ai_adapter)
        self.chains = {
            "job_is_interesting": self._create_chain(prompts.job_is_interesting),
            "text_question": self._create_chain(prompts.text_question_answer_template),
            "cover_letter": self._create_chain(prompts.coverletter_template),
            "personal_information": self._create_chain(prompts.personal_information_template),
            "legal_authorization": self._create_chain(prompts.legal_authorization_template),
            "work_preferences": self._create_chain(prompts.work_preferences_template),
            "education_details": self._create_chain(prompts.education_details_template),
            "experience_details": self._create_chain(prompts.experience_details_template),
            "projects": self._create_chain(prompts.projects_template),
            "availability": self._create_chain(prompts.availability_template),
            "salary_expectations": self._create_chain(prompts.salary_expectations_template),
            "certifications": self._create_chain(prompts.certifications_template),
            "languages": self._create_chain(prompts.languages_template),
            "interests": self._create_chain(prompts.interests_template),
            "previous_job_details": self._create_chain(prompts.previous_job_template),
            "general_knowledge_questions": self._create_chain(prompts.general_knowledge_template),
        }

    @staticmethod
    def find_best_match(text: str, options: list[str]) -> str:
        """
        Находим наилучшее совпадение строки с одним из вариантов
        и возвращаем лучший вариант из списка.
        """
        logger.info(f"Поиск лучшего совпадения для текста: '{text}' в вариантах: {options}")
        distances = [(option, distance(text.lower(), option.lower())) for option in options]
        best_option = min(distances, key=lambda x: x[1])[0]
        logger.info(f"Лучшее совпадение найдено: {best_option}")
        return best_option

    @staticmethod
    def _remove_placeholders(text: str) -> str:
        """Удаляем все заполнители 'PLACEHOLDER' из текста."""
        logger.debug("Удаление заполнителей из текста")
        return text.replace("PLACEHOLDER", "").strip()

    @staticmethod
    def _preprocess_template_string(template: str) -> str:
        """Преобразуем строку шаблона для использования в промптах."""
        logger.debug("Предобработка строки шаблона")
        return textwrap.dedent(template)

    def set_resume(self, resume: Dict[str, Any], resume_readable: str) -> None:
        """Добавляем резюме для анализа."""
        logger.info(f"Добавляем резюме: {resume}")
        self.resume = resume
        if (
            "salary_expectations" in self.resume
            and "currency" in self.resume["salary_expectations"]
        ):
            if self.resume["salary_expectations"]["currency"] == "RUR":
                self.resume["salary_expectations"]["currency"] = "руб"
        self.resume_readable = resume_readable

    def set_job(self, job) -> None:
        """Добавляем описание вакансии."""
        logger.info(f"Добавляем описание вакансии: {job}")
        self.job_description = job
        self.job_readable = transform_vacancy_data(job)

    def set_search_parameters(self, parameters: dict) -> None:
        """Устанавливаем параметры поиска вакансий."""
        logger.info(f"Устанавливаем параметры поиска вакансий: {parameters}")
        self.search_parameters = transform_search_config_data(parameters)

    def summarize_job_description(self, text: str) -> str:
        """Создаем краткое описание вакансии"""
        logger.info(f"Создаем краткое описание вакансии: '{text}'")
        prompts.summarize_prompt_template = self._preprocess_template_string(
            prompts.summarize_prompt_template
        )
        prompt = ChatPromptTemplate.from_template(prompts.summarize_prompt_template)
        chain = prompt | self.llm_cheap | StrOutputParser()
        output = chain.invoke({"text": text})
        logger.info(f"Сгенерировано краткое описание: {output}")
        return output

    def _create_chain(self, template: str) -> ChatPromptTemplate:
        """Создаем цепочку обработки для конкретного раздела резюме."""
        # logger.debug(f"Создание цепочки с шаблоном: '{template}'")
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm_cheap | StrOutputParser()

    def answer_question_textual_wide_range(self, question: str) -> str:
        """Определить тему заданного вопроса и ответить на него"""
        logger.info(f"Отвечаем на текстовый вопрос: '{question}'")
        sex = self.resume["personal_information"].get("sex")
        current_date = datetime.now().date().strftime("%Y-%m-%d")

        chain = self._create_chain(prompts.text_question_answer_template)
        output = chain.invoke(
            {
                "resume": self.resume_readable,
                "question": question,
                "sex": sex,
                "current_date": current_date,
            }
        )
        logger.info(f"Ответ на вопрос: {output}")
        return output

    def select_one_answer_from_options(self, question: str, options: list[str]) -> str:
        """
        Спрашиваем у LLM ответ на вопрос с несколькими
        вариантами ответа. Должен вернуть только один.
        """
        logger.info(f"Отвечаем на вопрос c выбором одного ответа: {question}")
        func_template = self._preprocess_template_string(prompts.options_template)
        prompt = ChatPromptTemplate.from_template(func_template)
        chain = prompt | self.llm_cheap | StrOutputParser()
        output_str = chain.invoke({"resume": self.resume, "question": question, "options": options})
        logger.info(f"Ответ от LLM: {output_str}")
        best_option = self.find_best_match(output_str, options)
        logger.info(f"Лучший вариант ответа найден: {best_option}")
        return best_option

    def select_many_answers_from_options(self, question: str, options: list[str]) -> List[str]:
        """
        Спрашиваем у LLM ответ на вопрос с одним или несколькими
        вариантами ответа. Может вернуть больше одного.
        """
        logger.info(f"Отвечаем на вопрос c выбором одного или нескольких ответа: {question}")
        func_template = self._preprocess_template_string(prompts.many_options_template)
        prompt = ChatPromptTemplate.from_template(func_template)
        chain = prompt | self.llm_cheap | StrOutputParser()
        output_str = chain.invoke({"resume": self.resume, "question": question, "options": options})
        logger.info(f"Ответ от LLM: {output_str}")
        # на случай если LLM вернет python-like список
        output_str = output_str.replace("[", "").replace("]", "")
        output_str = output_str.replace("'", "").replace("'", "")
        outputs = output_str.split(";")
        best_options = []
        for output in outputs:
            best_option = self.find_best_match(output, options)
            best_options.append(best_option)
        logger.info(f"Лучшие варианты ответа: {best_options}")
        return best_options

    def job_is_interesting(self) -> bool | None:
        """
        Спрашиваем у LLM, может ли быть интересна
        данная вакансия с учетом нашего резюме, навыков и интересов
        """
        logger.info("Проверяем, насколько вакансия может быть интересна.")
        chain = self._create_chain(prompts.job_is_interesting)
        try:
            output = chain.invoke(
                {
                    "resume": self.resume_readable,
                    "job_description": self.job_readable,
                    "search_parameters": self.search_parameters,
                }
            )
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при вызове LLM\n{tb_str}")
            return None
        logger.info(f"Ответ LLM: '{output}'")
        # парсим ответ LLM
        try:
            score = re.search(r"Score: (\d+)", output).group(1)
            reasoning = re.search(r"Reasoning: (.+)", output, re.DOTALL).group(1)
        except AttributeError:
            logger.error(f"LLM вернула некорректный ответ:\n{output}")
            return False
        logger.info(f"Степень 'интересности' вакансии: {score}")
        if int(score) < JOB_IS_INTERESTING_THRESH:
            logger.info(f"Работа не интересна: {reasoning}")
            return False
        return True

    def resume_is_interesting(self) -> Tuple[str, str, str, str]:
        """
        Спрашиваем у LLM, наскольо может быть интересно
        данное резюме с точки зрения его улучшения
        """
        chain = self._create_chain(prompts.resume_is_interesting)
        try:
            output = chain.invoke(
                {
                    "resume": self.resume_readable,
                }
            )
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Ошибка при вызове LLM\n{tb_str}")
            return None
        # парсим ответ LLM
        try:
            demand_score = re.search(r"Demand Score: (\d+)", output).group(1)
            resume_score = re.search(r"Resume Score: (\d+)", output).group(1)
            solvency_score = re.search(r"Solvency Score: (\d+)", output).group(1)
            reasoning = re.search(r"Reasoning: (.+)", output, re.DOTALL).group(1)
        except AttributeError:
            logger.error(f"LLM вернула некорректный ответ:\n{output}")
            return False
        return demand_score, resume_score, solvency_score, reasoning

    def write_cover_letter(self) -> str:
        """
        Создаем сопроводительное письмо на основе резюме и описания вакансии.
        """
        # в зависимости от доступности того или иного контакта задаем его в промпте
        sex = self.resume["personal_information"].get("sex")
        telegram = self.resume["personal_information"].get("telegram", "")
        whatsapp = self.resume["personal_information"].get("whatsapp", "")
        phone = self.resume["personal_information"].get("phone", "")
        email = self.resume["personal_information"].get("email", "")
        preferred_contact = self.resume["personal_information"].get("preferred_contact")
        additional_prompt = "- В качестве контакта укажи "
        invoke_dict = {
            "resume": self.resume_readable,
            "job_description": self.job_readable,
            "sex": sex,
        }
        if telegram:
            additional_prompt += f"Telegram: {telegram}"
            invoke_dict["telegram"] = telegram
        elif whatsapp:
            additional_prompt += f"Whatsapp: {whatsapp}"
            invoke_dict["whatsapp"] = whatsapp
        elif preferred_contact == "phone":
            additional_prompt += f"Телефон: {phone}"
            invoke_dict["phone"] = phone
        elif preferred_contact == "email":
            additional_prompt += f"Email: {email}"
            invoke_dict["email"] = email
        elif phone:
            additional_prompt += f"Телефон: {phone}"
            invoke_dict["phone"] = phone
        else:
            additional_prompt += f"Email: {email}"
            invoke_dict["email"] = email

        chain = self._create_chain(prompts.coverletter_template + additional_prompt)
        output = chain.invoke(invoke_dict)
        logger.info(f"Сопроводительное письмо сгенерировано: '{output}'")
        return output

    def resume_improvement_recommendations(self) -> str:
        """
        Пишем рекомендации по улучшению резюме
        """
        logger.info("Пишем рекомендации по улучшению резюме")
        chain = self._create_chain(prompts.resume_improve)
        output = chain.invoke(
            {
                "resume": self.resume_readable,
            }
        )
        logger.info(f"Рекомендации по улучшению резюме сгенерированы: '{output}'")
        return output

    def parse_contacts(self, resume_info: str) -> Dict[str, str]:
        """
        Парсим контакты из резюме и возвращаем их в виде словаря.
        """
        logger.info("Парсим контакты из резюме")
        chain = self._create_chain(prompts.parse_contacts_template)
        output = chain.invoke(
            {
                "resume": resume_info,
            }
        )
        contacts = {}
        for key in ["Telegram", "Whatsapp", "Phone", "Email", "LinkedIn"]:
            contacts[key] = "No info"
            value = re.search(rf"{key}: (.+?)(?:\n|$)", output)
            if value:
                contacts[key] = value.group(1)
        logger.info(f"Контакты из резюме: {contacts}")
        return contacts


# class GPTResumeGenerator:
#     def __init__(self, config: dict, llm_api_key: str, llm_proxy: str):
#         self.ai_adapter = AIAdapter(config, llm_api_key, llm_proxy)
#         self.llm_cheap = LoggerChatModel(self.ai_adapter)
#         self.llm_embeddings = OpenAIEmbeddings(openai_api_key=llm_api_key, openai_proxy=llm_proxy)

#     @staticmethod
#     def _preprocess_template_string(template: str) -> str:
#         """Предобработка строки с целью убрать лишние отступы"""
#         return textwrap.dedent(template)

#     def set_resume(self, resume):
#         """Добавляем резюме для анализа."""
#         self.resume = resume

#     def set_job_description_from_text(self, job_description_text):
#         """Резюмируем описание вакансии"""
#         logger.info("Генерация краткого описания вакансии")
#         prompt = ChatPromptTemplate.from_template(prompts.summarize_prompt_template)
#         chain = prompt | self.llm_cheap | StrOutputParser()
#         output = chain.invoke({"text": job_description_text})
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Краткое описание вакансии сгенерировано")
#         self.job_description = output

#     def generate_header(self) -> str:
#         """Генерация заголовка резюме"""
#         logger.info("Генерация заголовка резюме")
#         header_prompt_template = self._preprocess_template_string(prompts.prompt_header)
#         prompt = ChatPromptTemplate.from_template(header_prompt_template)
#         chain = prompt | self.llm_cheap | StrOutputParser()

#         sex = self.resume["personal_information"].get("sex")
#         output = chain.invoke(
#             {
#                 "personal_information": self.resume["personal_information"],
#                 "job_description": self.job_readable,
#                 "sex": sex,
#             }
#         )
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Заголовок резюме сгенерирован")
#         return output

#     def generate_education_section(self) -> str:
#         """Генерация раздела образования для резюме"""
#         logger.info("Генерация раздела образования для резюме")
#         education_prompt_template = self._preprocess_template_string(prompts.prompt_education)
#         prompt = ChatPromptTemplate.from_template(education_prompt_template)
#         chain = prompt | self.llm_cheap | StrOutputParser()
#         sex = self.resume["personal_information"].get("sex")
#         output = chain.invoke(
#             {
#                 "education_details": self.resume["education_details"],
#                 "job_description": self.job_readable,
#                 "sex": sex,
#             }
#         )
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Раздел образования сгенерирован")
#         return output

#     def generate_work_experience_section(self) -> str:
#         """Генерация раздела опыта для резюме"""
#         logger.info("Генерация раздела опыта для резюме")
#         work_experience_prompt_template = self._preprocess_template_string(
#             prompts.prompt_working_experience
#         )
#         prompt = ChatPromptTemplate.from_template(work_experience_prompt_template)
#         chain = prompt | self.llm_cheap | StrOutputParser()
#         sex = self.resume["personal_information"].get("sex")
#         output = chain.invoke(
#             {
#                 "experience_details": self.resume["experience_details"],
#                 "job_description": self.job_readable,
#                 "sex": sex,
#             }
#         )
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Раздел опыта сгенерирован")
#         return output

#     def generate_side_projects_section(self) -> str:
#         """Генерация раздела проектов для резюме"""
#         logger.info("Генерация раздела проектов для резюме")

#         side_projects_prompt_template = self._preprocess_template_string(
#             prompts.prompt_side_projects
#         )

#         prompt = ChatPromptTemplate.from_template(side_projects_prompt_template)

#         chain = prompt | self.llm_cheap | StrOutputParser()
#         sex = self.resume["personal_information"].get("sex")

#         output = chain.invoke(
#             {
#                 "projects": self.resume["about_me"],
#                 "job_description": self.job_readable,
#                 "sex": sex,
#             }
#         )
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Раздел проектов сгенерирован")
#         return output

#     def generate_achievements_section(self) -> str:
#         """Генерация раздела достижений для резюме"""
#         logger.info("Генерация раздела достижений для резюме")

#         achievements_prompt_template = self._preprocess_template_string(prompts.prompt_achievements)

#         prompt = ChatPromptTemplate.from_template(achievements_prompt_template)

#         chain = prompt | self.llm_cheap | StrOutputParser()

#         sex = self.resume["personal_information"].get("sex")
#         input_data = {
#             "achievements": self.resume["about_me"],
#             "job_description": self.job_readable,
#             "sex": sex,
#         }

#         output = chain.invoke(input_data)
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Раздел достижений сгенерирован")
#         return output

#     def generate_certifications_section(self) -> str:
#         """Генерация раздела сертификации для резюме"""
#         logger.info("Генерация раздела сертификации для резюме")

#         certifications_prompt_template = self._preprocess_template_string(
#             prompts.prompt_certifications
#         )

#         prompt = ChatPromptTemplate.from_template(certifications_prompt_template)

#         chain = prompt | self.llm_cheap | StrOutputParser()

#         sex = self.resume["personal_information"].get("sex")
#         input_data = {
#             "certifications": self.resume["certifications"],
#             "job_description": self.job_readable,
#             "sex": sex,
#         }

#         output = chain.invoke(input_data)
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Раздел сертификации сгенерирован")
#         return output

#     def generate_additional_skills_section(self) -> str:
#         """Генерация раздела навыков для резюме"""
#         logger.info("Генерация раздела навыков для резюме")

#         additional_skills_prompt_template = self._preprocess_template_string(
#             prompts.prompt_additional_skills
#         )
#         prompt = ChatPromptTemplate.from_template(additional_skills_prompt_template)
#         chain = prompt | self.llm_cheap | StrOutputParser()

#         sex = self.resume["personal_information"].get("sex")

#         output = chain.invoke(
#             {
#                 "languages": self.resume["languages"],
#                 "skills": self.resume["skills"],
#                 "job_description": self.job_readable,
#                 "sex": sex,
#             }
#         )
#         logger.info(f"Ответ от LLM: {output}")
#         logger.info("Раздел навыков сгенерирован")
#         return output

#     def generate_html_resume(self) -> str:
#         """Создание резюме из сгенерированных компонентов"""

#         def header_fn():
#             if self.resume["personal_information"] and self.job_description:
#                 return self.generate_header()
#             return ""

#         def education_fn():
#             if self.resume["education_details"] and self.job_description:
#                 return self.generate_education_section()
#             return ""

#         def work_experience_fn():
#             if self.resume["experience_details"] and self.job_description:
#                 return self.generate_work_experience_section()
#             return ""

#         def side_projects_fn():
#             if self.resume["about_me"] and self.job_description:
#                 return self.generate_side_projects_section()
#             return ""

#         def achievements_fn():
#             if self.resume["about_me"] and self.job_description:
#                 return self.generate_achievements_section()
#             return ""

#         def certifications_fn():
#             if self.resume["certifications"] and self.job_description:
#                 return self.generate_certifications_section()
#             return ""

#         def additional_skills_fn():
#             if (
#                 self.resume["experience_details"]
#                 or self.resume["education_details"]
#                 or self.resume["languages"]
#                 or self.resume["about_me"]
#             ) and self.job_description:
#                 return self.generate_additional_skills_section()
#             return ""

#         # Create a dictionary to map the function names to their respective callables
#         functions = {
#             "header": header_fn,
#             "education": education_fn,
#             "work_experience": work_experience_fn,
#             "side_projects": side_projects_fn,
#             "achievements": achievements_fn,
#             "certifications": certifications_fn,
#             "additional_skills": additional_skills_fn,
#         }

#         # Use ThreadPoolExecutor to run the functions in parallel
#         with ThreadPoolExecutor() as executor:
#             future_to_section = {executor.submit(fn): section for section, fn in functions.items()}
#             results = {}
#             for future in as_completed(future_to_section):
#                 section = future_to_section[future]
#                 try:
#                     result = future.result()
#                     if result:
#                         results[section] = result
#                 except Exception:
#                     tb_str = traceback.format_exc()
#                     logger.error(f"Секция {section} обработана с ошибкой\n{tb_str}")
#         full_resume = "<body>\n"
#         full_resume += f"  {results.get('header', '')}\n"
#         full_resume += "  <main>\n"
#         full_resume += f"    {results.get('education', '')}\n"
#         full_resume += f"    {results.get('work_experience', '')}\n"
#         full_resume += f"    {results.get('side_projects', '')}\n"
#         full_resume += f"    {results.get('achievements', '')}\n"
#         full_resume += f"    {results.get('certifications', '')}\n"
#         full_resume += f"    {results.get('additional_skills', '')}\n"
#         full_resume += "  </main>\n"
#         full_resume += "</body>"
#         return full_resume
