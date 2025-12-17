import asyncio
import os
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Page, Locator

from src.logger_config import logger
from src.telegram.telegram_manager import process_captcha
from src.utils.browser_utils import (
    create_playwright_browser,
    save_browser_session,
    safe_click,
    safe_fill,
    get_clean_text,
)
from src.utils.utils import sanitize_text


class PlaywrightJobManager:
    """
    Manages Playwright browser instance, authentication, and high-level interactions.
    Replaces HeadHunterAPI and Authenticator.
    """

    def __init__(self, secrets: dict):
        self.secrets = secrets
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.login = secrets.get("hh_login")
        self.password = secrets.get("hh_password")

    async def initialize(self):
        """Initialize browser, context, and page."""
        if not self.browser:
            self.browser, self.context, self.page = await create_playwright_browser()

    async def close(self):
        """Close browser resources."""
        if self.context:
            await save_browser_session(self.context)
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        self.page = None

    async def ensure_logged_in(self) -> bool:
        """Check if logged in, if not, perform login."""
        if not self.page:
            await self.initialize()
        logger.info("Checking login status...")
        await asyncio.sleep(2)
        if not await self._is_logged_in():
            return await self._perform_login()
        return True

    async def _perform_login(self) -> bool:
        """Perform login flow."""
        # Click login button
        if not await safe_click(self.page, "//*[contains(@data-qa, 'login')]"):
            logger.error("Could not find login button")
            return False

        # Some flows show an account-type chooser first (employer vs applicant).
        # We always want applicant/employee ("Я ищу работу") flow.
        await asyncio.sleep(1)
        logger.info("Handling account type chooser")
        await self._handle_account_type_chooser_if_present()

        # HH may default credential type to PHONE; switch to EMAIL if the toggle exists.
        logger.info("Selecting email credential type")
        await self._select_email_credential_type_if_present()

        # Fill login (email) FIRST (HH can require it before switching to password form)
        await asyncio.sleep(1)
        logger.info("Filling login")
        await safe_fill(
            self.page,
            "//*[@data-qa='applicant-login-input-email']",
            self.login,
            wait_for_timeout=2000,
        )

        # Then open password form (button text: "Войти с паролем")
        logger.info("Opening password form")
        expand_pass = self.page.locator("//*[starts-with(@data-qa, 'expand-login-by')]")
        if await expand_pass.count() > 0:
            await expand_pass.click()
            await asyncio.sleep(1)

        # Fill password
        logger.info("Filling password")
        await safe_fill(
            self.page,
            "//*[@data-qa='login-input-password' or @data-qa='applicant-login-input-password']",
            self.password,
            wait_for_timeout=5000,
        )
        await asyncio.sleep(2)

        # Click submit (button text: "Войти"). Avoid clicking generic submit too early ("Дальше")
        await safe_click(self.page, "//*[@data-qa='submit-button']", timeout=5000)
        await asyncio.sleep(2)

        # Check for errors
        error_msg = self.page.locator("//*[@data-qa='account-login-error']")
        if await error_msg.count() > 0:
            text = await get_clean_text(error_msg.first)
            logger.error(f"Login error: {text}")
            return False

        # Verify login success
        if await self._is_logged_in():
            logger.info("Login successful.")
            return True

        logger.warning("Login verification failed.")
        return False

    async def _is_logged_in(self) -> bool:
        """Check if logged in."""
        logger.info("Navigating to login page...")
        await self.page.goto("https://hh.ru/employer")

        try:
            resume_menu = self.page.locator('[data-qa="mainmenu_profileAndResumes"]')
            create_resume_button = self.page.locator('[data-qa="mainmenu_createResume"]')

            if await resume_menu.count() > 0 or await create_resume_button.count() > 0:
                logger.info("User is already logged in.")
                return True
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
        return False

    async def _handle_account_type_chooser_if_present(self) -> None:
        """
        HH can show an intermediate page asking which account type to use.
        If it appears, select applicant ("Я ищу работу") and click "Войти".
        """
        if not self.page:
            return

        chooser_container = self.page.locator("//*[@data-qa='account-type-cards']")
        applicant_card = self.page.locator(
            "//*[contains(@data-qa,'account-type-card-APPLICANT')]/ancestor::label[1]"
        )
        submit_btn = self.page.locator("//*[@data-qa='submit-button']")

        try:
            has_container = (await chooser_container.count()) > 0
            has_applicant = (await applicant_card.count()) > 0
            has_submit = (await submit_btn.count()) > 0
        except Exception:
            return

        if not (has_container or (has_applicant and has_submit)):
            return

        logger.info("Account type chooser detected. Selecting applicant account...")

        # Click applicant card (stable by data-qa); fallback to text match.
        clicked = await safe_click(
            self.page,
            "//*[contains(@data-qa,'account-type-card-APPLICANT')]/ancestor::label[1]",
            timeout=5000,
        )
        if not clicked:
            await safe_click(
                self.page,
                "//*[.//span[@data-qa='cell-text-content' and contains(., 'Я') and contains(., 'ищу работу')]]",
                timeout=5000,
            )

        await safe_click(self.page, "//*[@data-qa='submit-button']", timeout=5000)
        await asyncio.sleep(1)

    async def _select_email_credential_type_if_present(self) -> None:
        """
        HH applicant login can show a credential type switcher (PHONE vs EMAIL).
        If present and PHONE is selected, switch to EMAIL ("Почта").
        """
        if not self.page:
            return

        switcher = self.page.locator("//*[@data-qa='credential-type-switch']")
        if (await switcher.count()) == 0:
            return

        # In HH markup, selected state can appear as data-qa="credential-type-PHONE checked"
        phone_checked = self.page.locator(
            "//*[contains(@data-qa,'credential-type-PHONE') and contains(@data-qa,'checked')]"
        )
        if (await phone_checked.count()) == 0:
            return

        logger.info("Credential type switch detected. Switching to EMAIL...")
        clicked = await safe_click(
            self.page,
            "//*[@data-qa='credential-type-EMAIL']/ancestor::label[1]",
            timeout=5000,
        )
        if not clicked:
            await safe_click(
                self.page,
                "//*[self::label or self::div][.//*[contains(., 'Почта')]]",
                timeout=5000,
            )
        await asyncio.sleep(0.5)

    async def _handle_captcha(self, submit_selector: str):
        """Handle captcha if it appears."""
        captcha_img = self.page.locator("//*[@data-qa='account-captcha-picture']")

        start_time = datetime.now()

        while await captcha_img.count() > 0:
            if (datetime.now() - start_time).total_seconds() > 3600:
                logger.error("Captcha not solved in 1 hour.")
                break

            logger.info("Captcha detected.")

            img_path = "captcha_image.png"
            message_id = str(int(datetime.now().timestamp() * 10**6))

            # Send captcha if we haven't already (or just always send fresh screenshot)
            try:
                await captcha_img.first.screenshot(path=img_path)
            except Exception as e:
                logger.error(f"Failed to save captcha image: {e}")
                break

            tg_token = self.secrets["tg_token"]
            tg_api_id = self.secrets.get("tg_api_id")
            tg_api_hash = self.secrets.get("tg_api_hash")
            tg_chat_id = self.secrets["tg_chat_id"]
            tg_topic_id = self.secrets["tg_captcha_topic_id"]

            # Send image
            await process_captcha(
                tg_token,
                tg_api_id,
                tg_api_hash,
                tg_chat_id,
                tg_topic_id,
                img_path,
                message_id,
                listen=False,
            )

            # Wait for answer
            answer = await process_captcha(
                tg_token,
                tg_api_id,
                tg_api_hash,
                tg_chat_id,
                tg_topic_id,
                img_path,
                message_id,
                listen=True,
            )

            if answer:
                logger.info(f"Received captcha answer: {answer}")
                await safe_fill(self.page, "//*[@data-qa='account-captcha-input']", answer)
                await safe_click(self.page, submit_selector)

                # Wait for reload/check
                await asyncio.sleep(5)
                if os.path.exists(img_path):
                    os.remove(img_path)
            else:
                await asyncio.sleep(5)

    async def pause_async(self, low=0.5, high=1.0):
        """Async pause."""
        await asyncio.sleep(random.uniform(low, high))

    async def search_vacancies(self, search_url: str) -> List[Dict[str, Any]]:
        """Search vacancies and return list of basic info."""
        logger.info(f"Navigating to search URL: {search_url}")
        try:
            await self.page.goto(search_url)
        except Exception as e:
            logger.error(f"Failed to load search URL: {e}")
            return []

        # Scrape results
        vacancies = []
        # Wait for results to load
        try:
            await self.page.wait_for_selector('[data-qa="vacancy-serp__vacancy"]', timeout=5000)
        except Exception:
            logger.warning("No vacancies found or timeout.")
            return []

        cards = await self.page.locator('[data-qa="vacancy-serp__vacancy"]').all()

        for card in cards:
            title_el = card.locator('[data-qa="serp-item__title"]')
            company_el = card.locator('[data-qa="vacancy-serp__vacancy-employer"]')

            if await title_el.count() > 0:
                url = await title_el.get_attribute("href")
                name = await get_clean_text(title_el)
                company = (
                    await get_clean_text(company_el) if await company_el.count() > 0 else "Unknown"
                )

                # Extract ID from URL
                match = re.search(r"vacancy/(\d+)", url)
                vac_id = match.group(1) if match else None

                if vac_id:
                    vacancies.append(
                        {
                            "id": vac_id,
                            "name": name,
                            "alternate_url": url.split("?")[0] if url else "",
                            "employer": {"name": company},
                        }
                    )

        return vacancies

    async def get_vacancy_full_info(self, vacancy_url: str) -> Dict[str, Any]:
        """Get full vacancy info for LLM."""
        if not self.page:
            await self.initialize()

        await self.page.goto(vacancy_url)
        description = ""
        desc_el = self.page.locator('[data-qa="vacancy-description"]')
        if await desc_el.count() > 0:
            description = await get_clean_text(desc_el)

        return {
            "description": description,
        }

    async def scrape_resume(self, resume_id: str) -> Dict[str, Any]:
        """Scrape resume data."""
        url = f"https://hh.ru/resume/{resume_id}"
        await self.page.goto(url)
        return {}

    async def _handle_interfering_messages(self):
        """Handle cookies and notifications."""
        # Cookies
        cookies_btn = self.page.locator("xpath=//*[text()='Понятно']")
        if await cookies_btn.count() > 0:
            await cookies_btn.click()

        # Notifications
        close_btn = self.page.locator('[data-qa="notification-close-button"]')
        if await close_btn.count() > 0:
            await close_btn.click()

    async def apply_to_vacancy(
        self, vacancy_url: str, cover_letter: str, gpt_answerer: Any, resume_titles: List[str]
    ) -> Tuple[str, str]:
        """
        Apply to vacancy. Returns (Result, Message).
        Result: 'Success', 'Skip', 'Error', 'Limit'
        """
        if self.page.url != vacancy_url:
            await self.page.goto(vacancy_url)

        await self.pause_async()

        # Click Apply
        apply_btn_top = self.page.locator('[data-qa="vacancy-response-link-top"]')
        apply_btn_bottom = self.page.locator('[data-qa="vacancy-response-link-bottom"]')

        apply_btn = None
        if await apply_btn_top.count() > 0:
            apply_btn = apply_btn_top
        elif await apply_btn_bottom.count() > 0:
            apply_btn = apply_btn_bottom

        if apply_btn:
            await apply_btn.first.click()
        else:
            # Check if already applied or other state
            return "Error", "Apply button not found"

        # Wait for modal or navigation
        await asyncio.sleep(2)
        await self._handle_interfering_messages()

        # Check if we are on response page (URL contains vacancy_response) or modal appeared
        # Sometimes it opens a modal, sometimes navigates.

        # Handle Questions
        questions = await self.page.locator('[data-qa="task-body"]').all()
        if questions:
            logger.info(f"Found {len(questions)} questions")
            for question in questions:
                success, msg = await self._handle_question(question, gpt_answerer)
                if not success:
                    return "Skip", msg

        # Handle Cover Letter
        cl_btn = self.page.locator(
            "xpath=//*[text()='Добавить' or contains(text(), 'Сопроводительное')]"
        )
        if await cl_btn.count() > 0 and await cl_btn.first.is_visible():
            await cl_btn.first.click()
            await asyncio.sleep(1)

        cl_input = self.page.locator('[data-qa="vacancy-response-popup-form-letter-input"]')
        if await cl_input.count() > 0:
            await safe_fill(
                self.page, '[data-qa="vacancy-response-popup-form-letter-input"]', cover_letter
            )

        await self._handle_interfering_messages()

        # Submit
        submit_btn = self.page.locator("xpath=//*[text()='Откликнуться']")
        if await submit_btn.count() > 0:
            await submit_btn.first.click()
            await asyncio.sleep(3)
            # Check for success?
            return "Success", ""

        return "Error", "Submit button not found"

    async def _handle_question(self, question: Locator, gpt_answerer: Any) -> Tuple[bool, str]:
        """Handle single question."""
        text_el = question
        # Need to find text of question. Usually it's direct text or child.
        question_text = await get_clean_text(text_el)
        logger.info(f"Handling question: {question_text}")

        # Radio
        radios = await question.locator('[data-qa="radio-container"]').all()
        if radios:
            options = []
            for r in radios:
                options.append(await get_clean_text(r))

            options.append("No info")
            answer = gpt_answerer.select_one_answer_from_options(question_text, options)

            for i, opt in enumerate(options):
                if opt == answer and opt != "No info":
                    await radios[i].click()
                    return True, ""
            return False, "No suitable answer found"

        # Checkbox
        checkboxes = await question.locator('[data-qa="checkbox-container"]').all()
        if checkboxes:
            options = []
            for c in checkboxes:
                options.append(await get_clean_text(c))

            options.append("No info")
            answers = gpt_answerer.select_many_answers_from_options(question_text, options)

            clicked = False
            for i, opt in enumerate(options):
                if opt in answers and opt != "No info":
                    await checkboxes[i].click()
                    clicked = True

            return clicked, "No suitable answer found" if not clicked else ""

        # Textarea
        textarea = question.locator("textarea")
        if await textarea.count() > 0:
            answer = gpt_answerer.answer_question_textual_wide_range(question_text)
            await textarea.fill(answer)
            return True, ""

        return False, "Unknown question type"

    async def get_my_resumes_from_browser(self) -> Dict[str, Any]:
        """Get resumes list via browser fetch or scraping."""
        await self.ensure_logged_in()
        # Open "Резюме и профиль" page from main menu
        menu_selector = '[data-qa="mainmenu_profileAndResumes"]'
        clicked = await safe_click(self.page, menu_selector, timeout=5000)
        if not clicked:
            await self.page.goto("https://hh.ru")
            await asyncio.sleep(1)
            await safe_click(self.page, menu_selector, timeout=5000)
        # Wait until resume cards are visible on the resumes/profile page
        try:
            await self.page.wait_for_selector('[data-qa="resume"]', timeout=15000)
        except Exception:
            logger.warning("Resume list not found after opening 'Резюме и профиль' page.")
            return {"items": []}

        def _extract_resume_id_from_href(href: Optional[str]) -> Optional[str]:
            if not href:
                return None
            match = re.search(r"/resume/([a-zA-Z0-9]+)", href)
            if match:
                return match.group(1)
            match = re.search(r"[?&]resume=([a-zA-Z0-9]+)", href)
            if match:
                return match.group(1)
            return None

        resumes: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        cards = await self.page.locator('[data-qa="resume"]').all()
        for card in cards:
            title = (await card.get_attribute("data-qa-title")) or ""
            title = title.strip()
            if not title:
                title_el = card.locator('[data-qa="title"]').first
                title = ((await title_el.text_content()) or "").strip()

            link = card.locator('a[href][data-qa^="resume-card-link-"]').first
            if await link.count() == 0:
                link = card.locator('a[href*="/resume/"], a[href*="/profile/resume?resume="]').first

            href = await link.get_attribute("href") if await link.count() > 0 else None
            resume_id = _extract_resume_id_from_href(href)
            if not resume_id:
                continue

            if resume_id in seen_ids:
                continue
            seen_ids.add(resume_id)

            resumes.append({"id": resume_id, "title": title})

        logger.info(f"Found {len(resumes)} resumes")

        return {"items": resumes}

    async def get_resume_content_from_browser(self, resume_id: str) -> Dict[str, Any]:
        """
        Open hh.ru resume page and scrape key sections.

        We keep backward compatibility by returning API-shaped data when possible,
        and always attaching scraped sections under `scraped_sections`.
        """

        resume = {}

        user_profile_url = "https://hh.ru/profile/me"
        await self.page.goto(user_profile_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        resume["first_name"] = await self._get_first_name()
        resume["last_name"] = await self._get_last_name()
        resume["contacts"] = {}
        resume["contacts"]["telegram"] = await self._get_telegram()
        resume["contacts"]["whatsapp"] = await self._get_whatsapp()
        resume["area"] = await self._get_area()
        resume["driving_license"] = await self._get_driving_license()

        resume_url = f"https://hh.ru/resume/{resume_id}"
        await self.page.goto(resume_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        resume["contacts"]["phone"] = await self._get_resume_phone()
        resume["contacts"]["email"] = await self._get_resume_email()
        resume["job_preferences"] = {}
        resume["job_preferences"]["job_type"] = await self._get_job_type()
        resume["job_preferences"]["job_format"] = await self._get_job_format()
        resume["job_preferences"]["time_to_travel"] = await self._get_time_to_travel()
        resume["job_preferences"][
            "readiness_to_job_trips"
        ] = await self._get_readiness_to_job_trips()
        resume["job_preferences"]["salary"] = await self._get_salary()
        resume["total_experience"] = await self._get_total_experience()
        resume["experience"] = await self._get_experience()
        resume["skills"] = await self._get_skills()
        resume["educations"] = await self._get_educations()
        resume["recommendations"] = await self._get_recommendations()
        resume["additional_education"] = await self._get_additional_education()
        resume["exams"] = await self._get_exams()
        resume["certificates"] = await self._get_certificates()

        resume_url = f"https://hh.ru/resume/edit/{resume_id}/about"
        await self.page.goto(resume_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        resume["about_me"] = await self._get_about_me()
        import code

        code.interact(local=dict(globals(), **locals()))
        return resume

    async def _get_first_name(self) -> str:
        first_name = self.page.locator('[data-qa="profile-common-card-firstname"]')
        if await first_name.count() > 0:
            first_name = await first_name.first.text_content()
            first_name = sanitize_text(first_name)
        return first_name

    async def _get_last_name(self) -> str:
        last_name = self.page.locator('[data-qa="profile-common-card-lastname"]')
        if await last_name.count() > 0:
            last_name = await last_name.first.text_content()
            last_name = sanitize_text(last_name)

    async def _get_telegram(self) -> str:
        telegram = self.page.locator("xpath=//*[contains(text(), 'Telegram')]")
        if await telegram.count() > 0:
            parent = telegram.first.locator("../../../../../../../..")
            telegram = await parent.text_content()
            telegram = telegram.replace("Telegram", "").strip()
            return telegram
        return ""

    async def _get_whatsapp(self) -> str:
        whatsapp = self.page.locator("xpath=//*[contains(text(), 'Whatsapp')]")
        if await whatsapp.count() > 0:
            parent = whatsapp.first.locator("../../../../../../../..")
            whatsapp = await parent.text_content()
            whatsapp = whatsapp.replace("Whatsapp", "").strip()
            return whatsapp
        return ""

    async def _get_area(self) -> str:
        area = self.page.locator("xpath=//*[contains(text(), 'Где живёте')]")
        if await area.count() > 0:
            parent = area.first.locator("../../../../../../../..")
            area = await parent.text_content()
            area = area.replace("Где живёте", "").strip()
            area = area.split("·")[0].strip()
            return area
        return ""

    async def _get_driving_license(self) -> str:
        driving_license = self.page.locator("xpath=//*[contains(text(), 'Опыт вождения')]")
        if await driving_license.count() > 0:
            parent = driving_license.first.locator("../../..")
            driving_license = await parent.text_content()
            driving_license = driving_license.replace("Опыт вождения", "").strip()
            driving_license = sanitize_text(driving_license)
            driving_license = driving_license.split("·")[0].strip()
            return driving_license
        return ""

    async def _get_resume_phone(self) -> str:
        phone = self.page.locator('[data-qa="resume-contact-phone-value-text"]')
        if await phone.count() > 0:
            phone = await phone.first.text_content()
            phone = sanitize_text(phone)
            return phone
        return ""

    async def _get_resume_email(self) -> str:
        email = self.page.locator('[data-qa="resume-contact-email-value-preferred-text"]')
        if await email.count() > 0:
            email = await email.first.text_content()
            email = sanitize_text(email)
            return email
        return ""

    async def _get_salary(self) -> str:
        salary = self.page.locator('[data-qa="title-description"]')
        if await salary.count() > 0:
            salary = await salary.text_content()
            salary = sanitize_text(salary)
            return salary
        return ""

    async def _get_job_type(self) -> str:
        job_type = self.page.locator("xpath=//*[contains(text(), 'Тип занятости:')]")
        if await job_type.count() > 0:
            parent = job_type.first.locator("..")
            job_type = await parent.text_content()
            job_type = sanitize_text(job_type)
            job_type = job_type.split(":")[1].strip()
            return job_type
        return ""

    async def _get_job_format(self) -> str:
        job_format = self.page.locator("xpath=//*[contains(text(), 'Формат работы:')]")
        if await job_format.count() > 0:
            parent = job_format.first.locator("..")
            job_format = await parent.text_content()
            job_format = sanitize_text(job_format)
            job_format = job_format.split(":")[1].strip()
            return job_format
        return ""

    async def _get_time_to_travel(self) -> str:
        time_to_travel = self.page.locator("xpath=//*[contains(text(), 'Желательное время')]")
        if await time_to_travel.count() > 0:
            parent = time_to_travel.first.locator("..")
            time_to_travel = await parent.text_content()
            time_to_travel = sanitize_text(time_to_travel)
            time_to_travel = time_to_travel.split(":")[1].strip()
            return time_to_travel
        return ""

    async def _get_readiness_to_job_trips(self) -> str:
        ready_to_job_trip = self.page.locator("xpath=//*[contains(text(), 'Командировки:')]")
        if await ready_to_job_trip.count() > 0:
            parent = ready_to_job_trip.first.locator("..")
            ready_to_job_trip = await parent.text_content()
            ready_to_job_trip = sanitize_text(ready_to_job_trip)
            ready_to_job_trip = ready_to_job_trip.split(":")[1].strip()
            return ready_to_job_trip
        return ""

    async def _get_total_experience(self) -> str:
        total_experience = self.page.locator("xpath=//*[contains(text(), 'Опыт работы:')]")
        if await total_experience.count() > 0:
            parent = total_experience.first.locator("..")
            total_experience = await parent.text_content()
            total_experience = sanitize_text(total_experience)
            total_experience = total_experience.split(":")[1].strip()
            return total_experience
        return ""

    async def _get_experience(self) -> str:
        experience = self.page.locator('[data-qa="resume-list-card-experience"]')
        group_locators = experience.locator('[class^="group--"]')
        experience_texts = await group_locators.all_text_contents()
        experience_texts = [
            text.replace("\u2009", "").replace("\xa0", " ") for text in experience_texts
        ]
        experience = "\n".join(experience_texts)
        return experience

    async def _get_skills(self) -> str:
        skill_card = self.page.locator("[data-qa='skills-card']")
        skills = skill_card.locator('[class^="magritte-tag__label"]')
        skills = await skills.all_text_contents()
        skills = "\n".join(skills)
        return skills

    async def _get_educations(self) -> str:
        education_card = self.page.locator("[data-qa='resume-list-card-education']")
        educations = education_card.locator('[data-qa="cell-text-content"]')
        educations = await educations.all_text_contents()
        educations = "\n".join(educations)
        return educations

    async def _get_about_me(self) -> str:
        about_me = self.page.locator("[data-qa='resume-editor-about']")
        about_me = await about_me.all_text_contents()
        about_me = "\n".join(about_me)
        return about_me

    async def _get_recommendations(self) -> str:
        recommendations = self.page.locator("[data-qa='resume-list-card-recommendation']")
        recommendations_locator = recommendations.locator('[data-qa="cell-text-content"]')
        recommendations = await recommendations_locator.all_text_contents()
        recommendations = "\n".join(recommendations)
        return recommendations

    async def _get_additional_education(self) -> str:
        additional_education = self.page.locator("[data-qa='resume-list-card-additionalEducation']")
        additional_education_locator = additional_education.locator('[data-qa="cell-text-content"]')
        additional_education = await additional_education_locator.all_text_contents()
        additional_education = "\n".join(additional_education)
        return additional_education

    async def _get_exams(self) -> str:
        exams = self.page.locator("[data-qa='resume-list-card-certificate']")
        exams_locator = exams.locator('[data-qa="cell-text-content"]')
        exams = await exams_locator.all_text_contents()
        exams = [
            r
            for r in exams
            if not (r == "Профориентация" or r.startswith("Тест поможет определить ваши"))
        ]
        exams = "\n".join(exams)
        return exams

    async def _get_certificates(self) -> str:
        certificates = self.page.locator("[data-qa='resume-list-card-certificate']")
        certificates_locator = certificates.locator('[data-qa="cell-text-content"]')
        certificates = await certificates_locator.all_text_contents()
        certificates = "\n".join(certificates)
        return certificates
