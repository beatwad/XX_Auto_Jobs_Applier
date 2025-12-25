import asyncio
import os
import random
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from Levenshtein import distance
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
        if not await safe_click(self.page, "[data-qa*='login']"):
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
        try:
            await self.page.goto("https://hh.ru/employer", timeout=10000)
            logger.info("Переход на страницу: https://hh.ru/employer")
        except Exception as e:
            logger.warning(f"Failed to navigate to login page: {e}")
            logger.info("Trying to continue...")

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
            "[data-qa*='account-type-card-APPLICANT']/ancestor::label[1]"
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
            "[data-qa*='credential-type-PHONE'] and [data-qa*='checked']"
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

    async def start_search(self, resume_id: str) -> None:
        url = f"https://hh.ru/resume/{resume_id}"
        await self.page.goto(url)
        logger.info(f"Переход на страницу: {url}")
        recommend_button = self.page.locator("xpath=//*[contains(text(), 'Подобрали для вас')]")
        if await recommend_button.count() > 0:
            await recommend_button.click()

    async def set_advanced_search_params(
        self, search_params: Dict[str, Any], resume_id: str
    ) -> None:
        """
        Зайти на страницу расширенного поиска hh.ru и выставить настройки из `search_config.yaml`.

        `search_params` ожидается в "сыром" виде (как в YAML / `SearchConfig.model_dump()`).
        """
        self.search_params = search_params or {}
        await self.start_search(resume_id)
        opened = False
        await self.pause_async(3, 4)
        for selector in (
            "[data-qa='advanced-search']",
            "[aria-label='Расширенный поиск']",
            "xpath=//*[contains(., 'Расширенный поиск')]",
        ):
            if await safe_click(self.page, selector, timeout=5000):
                opened = True
                break

        if not opened:
            logger.warning("Advanced search button not found; trying to open advanced search URL")
            try:
                await self.page.goto("https://hh.ru/search/vacancy/advanced")
                logger.info("Переход на страницу: https://hh.ru/search/vacancy/advanced")
            except Exception as e:
                logger.error(f"Failed to navigate to advanced search page: {e}")
                return

        # Wait for advanced-search UI to be present
        try:
            await self.page.wait_for_selector(
                "[data-qa='vacancysearch__keywords-input']", timeout=15000
            )
        except Exception:
            # UI sometimes loads under different qa; keep going best-effort
            pass

        await self._handle_interfering_messages()

        # 2) Apply settings (best-effort for each block)
        # TODO: добавить частоту выплат, график работы, рабочие часы, категорию прав
        await self._set_keywords()
        await self._set_search_field()
        await self._set_words_to_exclude()
        await self._set_professional_role()
        await self._set_industry()
        await self._set_area()
        await self._set_districts()
        await self._set_salary_and_currency()
        await self._set_only_with_salary()
        await self._set_education()
        await self._set_experience()
        await self._set_employment()
        await self._set_job_format()
        await self._set_vacancy_label()
        await self._set_order_by()
        await self._set_period()

        # 3) Start search
        await self._handle_interfering_messages()
        if not await safe_click(
            self.page, "[data-qa='advanced-search-submit-button']", timeout=10000
        ):
            await safe_click(
                self.page, "xpath=//*[text()='Найти' or text()='Найти вакансии']", timeout=5000
            )
        await asyncio.sleep(2)

    # -----------------------------
    # Advanced search helpers (UI)
    # -----------------------------

    @staticmethod
    def _split_multi(value: Any) -> List[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if not isinstance(value, str):
            return [str(value).strip()] if str(value).strip() else []
        # Accept both comma and semicolon separated input
        raw = value.replace(";", ",")
        return [v.strip() for v in raw.split(",") if v.strip()]

    @staticmethod
    def _true_keys(value: Any) -> List[str]:
        if not isinstance(value, dict):
            return []
        return [k for k, v in value.items() if v is True]

    @staticmethod
    def _first_true_key(value: Any) -> Optional[str]:
        keys = PlaywrightJobManager._true_keys(value)
        return keys[0] if keys else None

    async def _click_best_suggestion(self, desired: str, suggestion_xpath: str) -> bool:
        desired_norm = (desired or "").strip().lower()
        if not desired_norm:
            return False
        suggestions = self.page.locator(suggestion_xpath)
        try:
            await suggestions.first.wait_for(state="visible", timeout=5000)
        except Exception:
            return False

        items = await suggestions.all()
        if not items:
            return False

        texts: List[str] = []
        for item in items:
            t = (await item.text_content()) or ""
            t = re.sub(r"\s+", " ", t).strip()
            texts.append(t)

        distances = [
            (idx, distance(desired_norm, (texts[idx] or "").lower())) for idx in range(len(texts))
        ]
        best_idx = min(distances, key=lambda x: x[1])[0]
        try:
            await items[best_idx].click()
            await asyncio.sleep(0.5)
            return True
        except Exception:
            return False

    async def _set_keywords(self) -> None:
        logger.debug("Вводим ключевые слова")
        keywords = self.search_params.get("keywords") or self.search_params.get("text") or ""
        keywords = str(keywords).strip()
        if not keywords:
            return
        await safe_fill(
            self.page, "[data-qa='vacancysearch__keywords-input']", keywords, timeout=10000
        )
        # await self.pause_async(0.5, 1)
        # await self.page.keyboard.press("ArrowDown")
        # await self.pause_async(0.5, 1)
        # await self.page.keyboard.press("Enter")
        suggestion_xpath = (
            "//*[@data-qa='suggest-item-cell' or @data-qa='suggester__keywords-item']"
        )
        await self._click_best_suggestion(keywords, f"xpath={suggestion_xpath}")
        await asyncio.sleep(0.5)

    async def _set_search_field(self) -> None:
        logger.debug("Задаем настройки области поиска")
        search_field = self.search_params.get("search_field") or {}
        enabled = set(self._true_keys(search_field))
        if not enabled:
            return

        # New HH advanced search uses checkbox inputs: name="search_field", value in {name, company_name, description}
        # Click by input/label first (more stable than text), then fallback to old text-based clicking.
        for key in ("name", "company_name", "description"):
            if key not in enabled:
                continue

            clicked = await safe_click(
                self.page,
                f"xpath=//label[.//input[@name='search_field' and @value='{key}']]",
                timeout=5000,
            )
            if not clicked:
                # Old selenium-era fallback: click by visible text
                text_map = {
                    "name": "в названии вакансии",
                    "company_name": "в названии компании",
                    "description": "в описании вакансии",
                }
                await safe_click(
                    self.page,
                    f"xpath=//*[self::label or self::span or self::div][contains(., '{text_map[key]}')]",
                    timeout=5000,
                )
            await asyncio.sleep(0.2)

    async def _set_words_to_exclude(self) -> None:
        logger.debug("Задаем слова для исключения")
        words = self.search_params.get("words_to_exclude") or ""
        words = str(words).strip()
        if not words:
            return
        await safe_fill(
            self.page, "[data-qa='vacancysearch__keywords-excluded-input']", words, timeout=10000
        )
        await asyncio.sleep(0.5)

    async def _set_tree_selector_single(self, open_text: str, value: str) -> None:
        """
        Open a "tree selector" modal (specialization/industry), type value, pick best match, submit.
        """
        value = str(value or "").strip()
        if not value:
            return

        # Open modal
        opened = False
        for selector in (
            f"xpath=//*[normalize-space()='{open_text}']",
            f"xpath=//*[contains(., '{open_text}')]",
        ):
            if await safe_click(self.page, selector, timeout=5000):
                opened = True
                break
        if not opened:
            return

        await asyncio.sleep(0.5)
        search_input_xpath = "//*[@data-qa='tree-selector-search-input' or @data-qa='bloko-tree-selector-popup-search']"
        await safe_fill(self.page, f"xpath={search_input_xpath}", value, timeout=10000)
        await asyncio.sleep(0.8)

        # Suggestions inside modal
        suggestion_xpath = (
            "//*[starts-with(@data-qa, 'tree-selector-item') "
            "or starts-with(@data-qa, 'bloko-tree-selector-item-text') "
            "or @data-qa='suggest-item-cell']"
        )

        picked = await self._click_best_suggestion(value, f"xpath={suggestion_xpath}")
        if not picked:
            # close/cancel modal if nothing found
            await safe_click(
                self.page,
                "xpath=//*[@data-qa='composite-selection-tree-selector-modal-cancel' or @data-qa='bloko-tree-selector-popup-cancel']",
                timeout=3000,
            )
            return

        await asyncio.sleep(0.5)
        await safe_click(
            self.page,
            "xpath=//*[@data-qa='composite-selection-tree-selector-modal-submit' or @data-qa='bloko-tree-selector-popup-submit']",
            timeout=5000,
        )
        await asyncio.sleep(0.5)

    async def _set_professional_role(self) -> None:
        logger.debug("Задаем профессиональную роль")
        value = self.search_params.get("professional_role") or ""
        value = str(value).strip()
        if not value:
            return
        await self._set_tree_selector_single("Указать специализации", value)

    async def _set_industry(self) -> None:
        logger.debug("Задаем отрасль")
        value = self.search_params.get("industry") or ""
        value = str(value).strip()
        if not value:
            return
        await self._set_tree_selector_single("Указать отрасль компании", value)

    async def _set_area(self) -> None:
        logger.debug("Задаем регион")
        values = self._split_multi(self.search_params.get("area"))
        if not values:
            return

        input_selector = "[data-qa='advanced-search-region-add'] input"
        # Some HH versions use a custom input without <input>
        if await self.page.locator(input_selector).count() == 0:
            input_selector = "[data-qa='advanced-search-region-add']"

        suggestion_xpath = (
            "//*[@data-qa='suggest-item-cell' or @data-qa='suggester__keywords-item']"
        )
        for region in values:
            if not region:
                continue
            if not await safe_fill(self.page, input_selector, region, timeout=10000):
                await safe_click(self.page, input_selector, timeout=5000)
                await self.page.keyboard.type(region)
            await asyncio.sleep(0.7)
            await self._click_best_suggestion(region, f"xpath={suggestion_xpath}")

    async def _set_districts(self) -> None:
        logger.debug("Задаем районы")
        values = self._split_multi(self.search_params.get("districts"))
        if not values:
            return
        input_selector = "[data-qa='searchform__district-input']"
        if await self.page.locator(input_selector).count() == 0:
            return

        suggestion_xpath = (
            "//*[@data-qa='suggest-item-cell' or @data-qa='address-edit-district-suggest-item']"
        )
        for district in values:
            if not district:
                continue
            await safe_fill(self.page, input_selector, district, timeout=10000)
            await asyncio.sleep(0.7)
            await self._click_best_suggestion(district, f"xpath={suggestion_xpath}")

    async def _set_salary_and_currency(self) -> None:
        logger.debug("Задаем зарплату и валюту")
        salary = self.search_params.get("salary")
        if salary is not None and salary != "":
            try:
                salary_val = str(int(salary))
            except Exception:
                salary_val = str(salary)
            await safe_fill(
                self.page, "[data-qa='advanced-search-salary']", salary_val, timeout=10000
            )
            await asyncio.sleep(0.2)

        currency = self.search_params.get("currency") or {}
        currency_key = self._first_true_key(currency)
        if not currency_key:
            return

        # New HH UI uses "chips" with radio inputs: name="currency_code", data-qa="currency-code-RUR|EUR|USD"
        # Prefer clicking the label that contains the radio input (inputs may be visually hidden).
        clicked = await safe_click(
            self.page,
            f"xpath=//label[.//input[@name='currency_code' and (@value='{currency_key}' or @data-qa='currency-code-{currency_key}')]]",
            timeout=3000,
        )
        if clicked:
            await asyncio.sleep(0.2)
            return

        # Fallback: some older versions use a <select> or different container
        select_locator = self.page.locator(
            "select[name='currency'], [data-qa='advanced-search-currency'] select"
        )
        if await select_locator.count() > 0:
            try:
                await select_locator.first.select_option(currency_key)
                await asyncio.sleep(0.2)
                return
            except Exception:
                pass

        text_map = {"RUR": "руб", "USD": "USD", "EUR": "EUR"}
        await safe_click(
            self.page,
            f"xpath=//*[self::label or self::span or self::div][contains(translate(., 'РУБUSDЕUR', 'рубusdеur'), '{text_map.get(currency_key, currency_key).lower()}')]",
            timeout=2000,
        )

    async def _set_only_with_salary(self) -> None:
        logger.debug("Задаем фильтр только с зарплатой")
        only = self.search_params.get("only_with_salary")
        if only is not True:
            return
        # New HH UI: checkbox is input name="label" value="with_salary"
        if await safe_click(
            self.page,
            "xpath=//label[.//input[@name='label' and @value='with_salary']]",
            timeout=3000,
        ):
            await asyncio.sleep(0.2)
            return

        # Fallback: click by likely text (older versions)
        for t in (
            "Только с зарплатой",
            "Только с указанной зарплатой",
            "Только с указанием зарплаты",
            "Показывать только вакансии",
        ):
            if await safe_click(
                self.page,
                f"xpath=//*[self::label or self::span or self::div][contains(., '{t}')]",
                timeout=2000,
            ):
                await asyncio.sleep(0.2)
                return

    async def _set_education(self) -> None:
        logger.debug("Задаем образование")
        edu = self.search_params.get("education") or {}
        mapping = {
            "not_needed": "not_required_or_not_specified",
            "middle": "special_secondary",
            "higher": "higher",
        }
        for key in self._true_keys(edu):
            suffix = mapping.get(key)
            if not suffix:
                continue
            await safe_click(
                self.page,
                f"[data-qa='advanced-search__education-item-label_{suffix}']",
                timeout=3000,
            )

    async def _set_experience(self) -> None:
        logger.debug("Задаем опыт работы")
        exp = self.search_params.get("experience") or {}
        key = self._first_true_key(exp)
        if not key:
            return
        # YAML uses doesntMatter, HH uses doesNotMatter
        if key == "doesntMatter":
            key = "doesNotMatter"
        await safe_click(
            self.page, f"[data-qa='advanced-search__experience-item-label_{key}']", timeout=3000
        )

    async def _set_employment(self) -> None:
        logger.debug("Задаем тип занятости")
        employment = self.search_params.get("employment") or {}
        enabled = self._true_keys(employment)
        if not enabled:
            return

        for key in enabled:
            if key == "ACCEPT_TEMPORARY":
                await safe_click(
                    self.page,
                    "[data-qa='advanced-search__accept_temporary-item']",
                    timeout=3000,
                )
                await asyncio.sleep(0.2)
                continue

            if key == "INTERNSHIP":
                await safe_click(
                    self.page,
                    "xpath=//label[.//input[@name='label' and @value='internship']]",
                    timeout=3000,
                )
                await asyncio.sleep(0.2)
                continue

            await safe_click(
                self.page,
                f"xpath=//label[.//input[@name='employment_form' and @value='{key}']]",
                timeout=3000,
            )
            await asyncio.sleep(0.2)

    async def _set_job_format(self) -> None:
        logger.debug("Задаем формат работы")
        job_format = self.search_params.get("job_format") or {}
        enabled = self._true_keys(job_format)
        if not enabled:
            return

        for key in enabled:
            if await safe_click(
                self.page,
                f"[data-qa='advanced-search__work_format-item-label_{key}']",
                timeout=1500,
            ):
                await asyncio.sleep(0.2)
                continue

    async def _set_vacancy_label(self) -> None:
        logger.debug("Задаем метки вакансий")
        labels = self.search_params.get("vacancy_label") or {}
        for key in self._true_keys(labels):
            await safe_click(
                self.page, f"[data-qa='advanced-search__label-item-label_{key}']", timeout=3000
            )
            # advanced-search__label-item-label_accept_teens

    async def _set_order_by(self) -> None:
        logger.debug("Задаем сортировку")
        order_by = self.search_params.get("order_by") or {}
        key = self._first_true_key(order_by)
        if not key:
            return
        # relevance is typically default; still allow click if user asked.
        await safe_click(
            self.page, f"[data-qa='advanced-search__order_by-item-label_{key}']", timeout=3000
        )

    async def _set_period(self) -> None:
        logger.debug("Задаем период поиска")
        period = self.search_params.get("period") or {}
        key = self._first_true_key(period)
        if not key:
            return
        mapping = {
            "all_time": "0",
            "month": "30",
            "week": "7",
            "three_days": "3",
            "one_day": "1",
        }
        days = mapping.get(key)
        if days is None:
            return
        await safe_click(
            self.page, f"[data-qa='advanced-search__search_period-item-label_{days}']", timeout=3000
        )

    async def get_vacancies_from_page(self, page_num: int = 0) -> List[Dict[str, Any]]:
        """Получить вакансии с очередной страницы"""
        return await self.page.locator('[data-qa="vacancy"]').all()

    async def get_vacancy_full_info(self, vacancy_url: str) -> Dict[str, Any]:
        """Get full vacancy info for LLM."""
        if not self.page:
            await self.initialize()

        await self.page.goto(vacancy_url)
        logger.info(f"Переход на страницу: {vacancy_url}")
        description = ""
        desc_el = self.page.locator('[data-qa="vacancy-description"]')
        if await desc_el.count() > 0:
            description = await get_clean_text(desc_el)

        return {
            "description": description,
        }

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
            logger.info(f"Переход на страницу: {vacancy_url}")

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
            logger.info("Переход на страницу: https://hh.ru")
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
        await self.page.goto(user_profile_url)
        logger.info(f"Переход на страницу: {user_profile_url}")
        # await self.pause_async(3, 4)

        resume["personal_information"] = {}
        resume["personal_information"]["first_name"] = await self._get_first_name()
        resume["personal_information"]["last_name"] = await self._get_last_name()
        resume["personal_information"]["telegram"] = await self._get_telegram()
        resume["personal_information"]["whatsapp"] = await self._get_whatsapp()
        resume["area"] = await self._get_area()
        resume["driving_license"] = await self._get_driving_license()
        linkedin, habr_career = await self._get_other_links()
        if linkedin:
            resume["personal_information"]["linkedin"] = linkedin
        if habr_career:
            resume["personal_information"]["habr_career"] = habr_career
        await safe_click(self.page, "[data-qa='profile-common-card-edit']", timeout=5000)
        await self.pause_async(2, 3)
        middle_name = await self._get_middle_name()
        if middle_name:
            resume["personal_information"]["middle_name"] = middle_name
        (
            sex,
            citizenship,
            legal_auth,
        ) = await self._get_sex_citizenship_and_legal_auth()
        if sex:
            resume["personal_information"]["sex"] = sex
        if citizenship:
            resume["citizenship"] = citizenship
        if legal_auth:
            resume["legal_authorization"] = legal_auth

        resume_url = f"https://hh.ru/resume/{resume_id}"
        await self.page.goto(resume_url)
        logger.info(f"Переход на страницу: {resume_url}")
        await self.pause_async(2, 3)

        resume["personal_information"]["phone"] = await self._get_resume_phone()
        resume["personal_information"]["email"] = await self._get_resume_email()
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
        await self.raise_resume()

        resume_url = f"https://hh.ru/resume/edit/{resume_id}/about"
        await self.page.goto(resume_url)
        logger.info(f"Переход на страницу: {resume_url}")
        await self.pause_async(2, 3)
        resume["about_me"] = await self._get_about_me()
        return resume

    async def raise_resume(self) -> None:
        """Raise resume in search."""
        raise_btn = self.page.locator(
            "xpath=//*[contains(text(), 'Поднять в') and contains(text(), 'поиске')]"
        )
        if await raise_btn.count() > 0:
            await raise_btn.first.click()
            await asyncio.sleep(2)
            logger.info("Резюме успешно поднято")
        else:
            logger.info("Резюме пока нельзя поднять")

    async def _get_first_name(self) -> str:
        first_name = self.page.locator('[data-qa="profile-common-card-firstname"]')
        if await first_name.count() > 0:
            first_name = await first_name.first.text_content()
            first_name = sanitize_text(first_name, lowercase=False)
        return first_name

    async def _get_other_links(self) -> Tuple[str, str]:
        linkedin = ""
        habr_career = ""
        other_links = await self.page.locator(
            '[data-qa*="profile-other-communication-methods-card-row"]'
        ).all()
        for other_link in other_links:
            text = await other_link.text_content()
            text = text.replace("\u2009", "").replace("\xa0", " ")
            if "linkedin.com" in text:
                linkedin = text
            elif "habr.ru" in text:
                habr_career = text
        return linkedin, habr_career

    async def _get_middle_name(self) -> str:
        middle_name = self.page.locator('[data-qa*="profile-common-edit-middleName"]')
        if await middle_name.count() > 0:
            middle_name = await middle_name.first.get_attribute("value")
            middle_name = sanitize_text(middle_name, lowercase=False)
        return middle_name

    async def _get_sex_citizenship_and_legal_auth(self) -> Tuple[str, str, str]:
        select_activators = await self.page.locator('[data-qa="magritte-select-activator"]').all()
        sex = ""
        citizenship = ""
        work_permission = ""
        for select_activator in select_activators:
            text = await select_activator.text_content()
            text = text.replace("\u2009", "").replace("\xa0", " ")
            if text.startswith("Пол"):
                sex = text.replace("Пол", "").strip()
            elif text.startswith("Гражданство"):
                citizenship = text.replace("Гражданство", "").strip()
            elif text.startswith("Разрешение на работу"):
                work_permission = text.replace("Разрешение на работу", "").strip()
        return sex, citizenship, work_permission

    async def _get_last_name(self) -> str:
        last_name = self.page.locator('[data-qa="profile-common-card-lastname"]')
        if await last_name.count() > 0:
            last_name = await last_name.first.text_content()
            last_name = sanitize_text(last_name, lowercase=False)
        return last_name

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
            email = sanitize_text(email, lowercase=False)
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
