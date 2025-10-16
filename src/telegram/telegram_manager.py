import asyncio
from typing import Any, Dict, Union

from telethon import TelegramClient

from src.constants import SEARCH_CONFIG_FILE, SECRETS_FILE, TG_CHAT_ID, TG_REPORT_TOPIC_ID
from src.logger_config import logger
from src.utils.utils import load_yaml_file
from telegram import Bot
from telegram.error import TelegramError


# Send message with PTB
async def send_captcha(bot_token, chat_id, topic_id, img_path, message):
    bot = Bot(token=bot_token)
    await bot.send_photo(
        chat_id=chat_id, message_thread_id=topic_id, photo=open(img_path, "rb"), caption=message
    )


# Receive messages with Telethon
async def receive_messages(api_id: str, api_hash: str, chat_id: str, topic_id: str, message: str):
    client = TelegramClient("my-client", api_id, api_hash)
    async with client:
        messages_ = await client.get_messages(chat_id, limit=10, reply_to=topic_id)
        for message_ in messages_:
            if message_.reply_to_msg_id:
                reply_msg_id = message_.reply_to_msg_id
                reply_message = await client.get_messages(
                    chat_id, ids=reply_msg_id, reply_to=topic_id
                )
                if reply_message and reply_message.text == message:
                    return message_.text


def load_secrets(secrets_yaml_path: str):
    """Загружаем необходимые для работы Telegram бота ключи"""
    secrets = load_yaml_file(secrets_yaml_path)
    tg_token, tg_api_id, tg_api_hash = (
        secrets["tg_token"],
        secrets.get("tg_api_id"),
        secrets.get("tg_api_hash"),
    )
    return tg_token, tg_api_id, tg_api_hash


async def process_captcha(
    tg_token, tg_api_id, tg_api_hash, chat_id, topic_id, img_path, message, listen=False
) -> Union[str, None]:
    """Ищем каптчу и если нашли - пересылаем в чат для решения"""
    if not listen:
        # Send a message using PTB
        await send_captcha(tg_token, chat_id, topic_id, img_path, message)
    else:
        # Receive messages using Telethon
        return await receive_messages(tg_api_id, tg_api_hash, chat_id, topic_id, message)


class TelegramReportSender:
    """
    Класс для отправки сообщений об ошибке через Telegram.
    В случае ошибки в процессе отправки ждем и отправляем заново.
    """

    def __init__(self):
        telegram_bot_token = load_yaml_file(SECRETS_FILE)["tg_token"]
        self.bot = Bot(token=telegram_bot_token)
        self.chat_id = TG_CHAT_ID
        self.report_topic_id = TG_REPORT_TOPIC_ID
        self.user_id = load_yaml_file(SEARCH_CONFIG_FILE).get("user_id", "-1")
        self.message = ""

        # Ensure proper async loop handling
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()

    def send_telegram_report(
        self,
        login: str,
        resume: Dict[str, Any],
        success_applies_num: str,
        jobs_no_info: str,
        skill_stat: str,
        resume_recommendations: str,
        resume_component: Any,
    ) -> None:
        """
        После завершения рассылки резюме послать отчет, который будет содержать
        количество вакансий, на которые приложения откликнулось, список вакансий,
        на которые приложение по той или иной причине откликнуться не смогло,
        а также рекомендации по улучшению резюме
        """
        # добавляем контакты клиента
        telegram = resume["personal_information"].get("telegram", "")
        email = resume["personal_information"].get("email", "")
        whatsapp = resume["personal_information"].get("whatsapp", "")

        if login and "@" in login:
            header = f"Email клиента: {login}"
        elif email:
            email = resume_component.deanonymize_personal_information(email)
            header = f"Email клиента: {email}"
        elif telegram:
            telegram = resume_component.deanonymize_personal_information(telegram)
            header = f"Telegram клиента: {telegram}"
        elif whatsapp:
            whatsapp = resume_component.deanonymize_personal_information(whatsapp)
            header = f"Whatsapp клиента: {whatsapp}"
        else:
            header = f"ID клиента на hh.ru: {self.user_id} "

        first_name = resume["personal_information"].get("first_name", "")
        first_name = resume_component.deanonymize_personal_information(first_name)
        last_name = resume["personal_information"].get("last_name", "")
        last_name = resume_component.deanonymize_personal_information(last_name)
        middle_name = resume["personal_information"].get("middle_name", "")

        if middle_name:
            middle_name = resume_component.deanonymize_personal_information(middle_name)
            header += f"\nФИО клиента: {first_name} {middle_name} {last_name}\n"
        else:
            header += f"\nФИО клиента: {first_name} {last_name}\n"
        message = header
        message += f"Всего за прошедший день на сайте hh.ru успешно откликнулись на {success_applies_num} подходящих вам вакансий.\n"

        # добавить список вакансий, на которые ответить не получилось
        if jobs_no_info:
            message += "Ниже прилагаем список вакансий, на которые ответить не получилось ввиду отсутствия информации:\n\n"
            jobs_no_info = self._format_jobs_no_info(jobs_no_info)
            message += jobs_no_info

        # добавить статистику по наиболее востребованным вакансиям
        if skill_stat:
            message += "\nНиже прилагаем статистику по наиболее востребованным навыкам в интересующих вас вакансиях:\n\n"
            skill_stat = sorted(
                [(k, v) for k, v in skill_stat.items()], key=lambda x: x[1], reverse=True
            )[:20]
            for skill, stat in skill_stat:
                message += f"  {skill}: {stat}\n"

        # добавить рекомендации по улучшению резюме
        if resume_recommendations:
            message += "\nТакже прилагаем рекомендации по улучшению вашего резюме:\n\n"
            message += resume_recommendations

        self.message = message
        asyncio.run(self._send_chunked_messages(self.message, header))

    async def _send_chunked_messages(self, message, header):
        """
        Поскольку у Telegram есть ограничение длины сообщения в 4096 символов,
        посылаем отчет частями по 4096 символов
        """
        i = 0
        while i < len(message):
            if i == 0:
                part_message = message[:4096]
                i += 4096
            else:
                part_message = header + message[i : i + 4096 - len(header)]
                i += 4096 - len(header)
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    message_thread_id=self.report_topic_id,
                    text=part_message,
                )
            except TelegramError as e:
                logger.error(f"Failed to send Telegram report:\n{e}")
            await asyncio.sleep(3)  # Use async sleep

    def _format_jobs_no_info(self, jobs_no_info: list) -> str:
        """Отформатировать информацию о вакансиях, на которорые не смогли откликнуться"""
        res = ""
        for job_info in jobs_no_info:
            res += f"**Название вакансии:** {job_info['job_title']}\n"
            res += f"**Ссылка на вакансию:** {job_info['link']}\n"
            res += f"**Причина:** {job_info['reason']}\n\n"
        return res


if __name__ == "__main__":
    from src.constants import TG_CAPTCHA_TOPIC_ID

    message = "1747994625258759"
    tg_token, tg_api_id, tg_api_hash = load_secrets("data_folder/secrets/secrets.yaml")
    text = asyncio.run(
        receive_messages(tg_api_id, tg_api_hash, TG_CHAT_ID, TG_CAPTCHA_TOPIC_ID, message=message)
    )
    print(text)
