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
        try:
            await self.page.goto("https://hh.ru")
        except Exception as e:
            logger.error(f"Failed to load hh.ru: {e}")
            return False

        # Check for indicators of being logged in
        try:
            # Similar selectors to Authenticator.is_logged_in
            # Resume menu or Profile menu
            # We use short timeout for check
            resume_menu = self.page.locator('[data-qa="mainmenu_myResumes"]')
            profile_menu = self.page.locator('[data-qa="mainmenu_applicantProfile"]')

            if await resume_menu.count() > 0 or await profile_menu.count() > 0:
                logger.info("User is already logged in.")
                return True
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")

        logger.info("User not logged in. Starting login process.")
        return await self._perform_login()

    async def _perform_login(self) -> bool:
        """Perform login flow."""
        logger.info("Navigating to login page...")
        await self.page.goto("https://hh.ru/employer")

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
        if (
            await self.page.locator('[data-qa="mainmenu_myResumes"]').count() > 0
            or await self.page.locator('[data-qa="mainmenu_applicantProfile"]').count() > 0
        ):
            logger.info("Login successful.")
            return True

        logger.warning("Login verification failed.")
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
        await self.ensure_logged_in()
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
        await self.ensure_logged_in()
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
        await self.ensure_logged_in()
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

        # Select resume
        await self._select_correct_resume(resume_titles)

        # Handle Questions
        questions = await self.page.locator('xpath=//*[@data-qa="task-body"]').all()
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

    async def _select_correct_resume(self, resume_titles: List[str]):
        """Select correct resume if multiple available."""
        # This is simplified. In real flow we might need to expand list.
        # Check current selected resume
        pass

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
        try:
            # Try fetching via browser context (uses cookies/session)
            data = await self.page.evaluate("""async () => {
                const response = await fetch('https://api.hh.ru/resumes/mine', {
                    method: 'GET'
                });
                if (response.ok) {
                    return await response.json();
                }
                throw new Error('Fetch failed ' + response.status);
            }""")
            return data
        except Exception as e:
            logger.warning(f"Browser fetch for resumes failed: {e}. Trying scraping.")
            # Fallback to scraping
            if self.page.url != "https://hh.ru/applicant/resumes":
                await self.page.goto("https://hh.ru/applicant/resumes")

            resumes = []
            links = await self.page.locator('a[href*="/resume/"]').all()
            seen_ids = set()

            for link in links:
                href = await link.get_attribute("href")
                if href and "/resume/" in href:
                    match = re.search(r"/resume/([a-zA-Z0-9]+)", href)
                    if match:
                        rid = match.group(1)
                        if rid not in seen_ids and len(rid) > 10:
                            seen_ids.add(rid)
                            title = await get_clean_text(link)
                            resumes.append({"id": rid, "title": title})
            return {"items": resumes}

    async def get_resume_content_from_browser(self, resume_id: str) -> Dict[str, Any]:
        """Get resume content via browser fetch."""
        await self.ensure_logged_in()
        try:
            resume_data = await self.page.evaluate(f"""async () => {{
                const response = await fetch('https://api.hh.ru/resumes/{resume_id}', {{
                    method: 'GET'
                }});
                if (response.ok) {{
                    return await response.json();
                }}
                throw new Error('Fetch failed ' + response.status);
            }}""")
            return resume_data
        except Exception as e:
            logger.error(f"Failed to fetch resume data via browser: {e}")
            return {}

    async def publish_resume_browser(self, resume_id: str) -> bool:
        """Publish resume using browser fetch."""
        await self.ensure_logged_in()
        try:
            await self.page.evaluate(f"""async () => {{
                await fetch('https://api.hh.ru/resumes/{resume_id}/publish', {{
                    method: 'POST'
                }});
            }}""")
            return True
        except Exception as e:
            logger.error(f"Failed to publish resume: {e}")
            return False

    async def api_request(
        self, url: str, method: str = "GET", params: dict = None, data: dict = None
    ) -> Dict[str, Any]:
        """Make API request using browser context."""
        # Ensure logged in
        if not self.page:
            await self.initialize()

        # Use playwright request context
        response = await self.context.request.fetch(url, method=method, params=params, data=data)
        if response.status == 200:
            return await response.json()
        else:
            logger.error(f"API request failed: {response.status} {response.status_text}")
            return {}
