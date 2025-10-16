from string import Template
from typing import Any


class ResumeGenerator:
    """Класс для генерации резюме"""

    def __init__(self):
        self.html_template = """
                            <!DOCTYPE html>
                            <html lang="en">
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>Resume</title>
                                <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&display=swap" rel="stylesheet" />
                                <link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;600&display=swap" rel="stylesheet" />
                                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" />
                                <link rel="stylesheet" href="$style_path">
                            </head>
                            $markdown
                            </body>
                            </html>
                            """

    def create_resume(
        self, gpt_resume_generator: Any, style_path: str, job_description_text: str, temp_html_path
    ):
        """Генерация резюме"""
        gpt_resume_generator.set_job_description_from_text(job_description_text)
        self._create_resume(gpt_resume_generator, style_path, temp_html_path)

    def _create_resume(self, gpt_resume_generator: Any, style_path, temp_html_path):
        """Вспомогательный метод для генерации резюме"""
        template = Template(self.html_template)
        html_resume = gpt_resume_generator.generate_html_resume()
        message = template.substitute(markdown=html_resume, style_path=style_path)
        with open(temp_html_path, "w", encoding="utf-8") as temp_file:
            temp_file.write(message)
