import os
import tempfile
import webbrowser
from pathlib import Path

import inquirer

from src.logger_config import logger
from src.resume_builder.utils import HTML_to_PDF


class FacadeManager:
    """Класс интерфейса с генератором резюме"""

    def __init__(self, api_key, style_manager, resume_generator, log_path):
        # Получить полный путь к каталогу библиотеки
        lib_directory = Path(__file__).resolve().parent
        styles_directory = lib_directory / "resume_style"
        self.style_manager = style_manager
        self.style_manager.set_styles_directory(styles_directory)
        self.resume_generator = resume_generator
        self.selected_style = None  # свойства для хранения выбранного стиля

    def prompt_user(self, choices: list[str], message: str) -> str:
        questions = [
            inquirer.List("selection", message=message, choices=choices),
        ]
        return inquirer.prompt(questions)["selection"]

    def choose_style(self):
        """Выбор стиля резюме"""
        styles = self.style_manager.get_styles()
        if not styles:
            logger.warning("Нет доступных стилей")
            return None
        final_style_choice = "Создать свой стиль в CSS"
        formatted_choices = self.style_manager.format_choices(styles)
        formatted_choices.append(final_style_choice)
        selected_choice = self.prompt_user(
            formatted_choices, "Какой стиль резюме вы бы хотели использовать?"
        )
        if selected_choice == final_style_choice:
            tutorial_url = "https://github.com/feder-cr/lib_resume_builder_AIHawk/blob/main/how_to_contribute/web_designer.md"
            logger.info("\nОткрываем туториал в вашем браузере...")
            webbrowser.open(tutorial_url)
            exit()
        else:
            self.selected_style = selected_choice.split(" (")[0]

    def pdf_base64(self, gpt_resume_generator, job_description_text):
        """Создание PDF файла из сгенерированного HTML шаблона"""
        if self.selected_style is None:
            raise ValueError("Перед созданием PDF-файла необходимо выбрать стиль.")

        style_path = self.style_manager.get_style_path(self.selected_style)

        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".html", encoding="utf-8"
        ) as temp_html_file:
            temp_html_path = temp_html_file.name
            self.resume_generator.create_resume(
                gpt_resume_generator, style_path, job_description_text, temp_html_path
            )

        pdf_base64 = HTML_to_PDF(temp_html_path)
        os.remove(temp_html_path)
        return pdf_base64
