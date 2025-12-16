import asyncio
import base64
import os
import random
import re
import time
from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.app_config import HEADLESS_MODE
from src.constants import BROWSER_STORAGE_STATE
from src.logger_config import logger


def ensure_playwright_profile() -> str:
    """Ensure Playwright session directory exists"""
    logger.info(f"Ensuring Playwright session directory exists at: {BROWSER_STORAGE_STATE}")
    session_dir = os.path.dirname(BROWSER_STORAGE_STATE)
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
        logger.debug(f"Created Playwright session directory: {session_dir}")
    return session_dir


def get_playwright_browser_options() -> Dict[str, Any]:
    """Get Playwright browser launch options with LinkedIn-optimized settings"""
    logger.info("Configuring Playwright browser options")
    ensure_playwright_profile()

    launch_options = {
        "headless": HEADLESS_MODE,
        "args": [
            "--window-position=0,0",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--ignore-certificate-errors",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-translate",
            "--disable-popup-blocking",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-logging",
            "--disable-autofill",
            "--disable-plugins",
            "--disable-blink-features=AutomationControlled",
        ],
        # "ignore_default_args": ["--enable-automation", "--enable-logging"],
    }

    # Context options for session persistence and anti-detection
    context_options = {
        "viewport": {"width": 1920, "height": 1080},
        "screen": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "locale": "en-US",
        "permissions": ["notifications"],
        "storage_state": BROWSER_STORAGE_STATE if os.path.exists(BROWSER_STORAGE_STATE) else None,
    }

    return {"launch_options": launch_options, "context_options": context_options}


async def create_playwright_browser() -> tuple[Browser, BrowserContext, Page]:
    """Create Playwright browser, context and page asynchronously (PRIMARY METHOD)"""
    logger.info("Creating Playwright browser (async)")

    try:
        playwright = await async_playwright().start()
        options = get_playwright_browser_options()

        browser = await playwright.chromium.launch(**options["launch_options"])
        context = await browser.new_context(**options["context_options"])

        page = await context.new_page()

        logger.info("Playwright browser created successfully")
        return browser, context, page

    except Exception as e:
        logger.error(f"Failed to create Playwright browser: {e}")
        raise


async def save_browser_session(context: BrowserContext) -> None:
    """Save Playwright session state (async)"""
    try:
        ensure_playwright_profile()
        storage_state = await context.storage_state()

        with open(BROWSER_STORAGE_STATE, "w") as f:
            import json

            json.dump(storage_state, f)

        logger.info(f"Playwright session saved to {BROWSER_STORAGE_STATE}")
    except Exception as e:
        logger.error(f"Failed to save Playwright session: {e}")


async def safe_click(
    page: Page, selector: str, timeout: int = 1000, element_number: int = 0
) -> bool:
    """Safely click element with retries (async)"""
    try:
        locator = page.locator(selector)
        element_count = await locator.count()

        if element_count == 0:
            logger.warning(f"Element not found: {selector}")
            return False

        # Select the first matched element (even if multiple)
        target = locator.nth(element_number) if element_count > 1 else locator

        if element_count > 1:
            logger.debug(
                f"Found {element_count} elements for selector '{selector}', using the first match"
            )

        # Ensure visibility and bring into view
        try:
            await target.wait_for(state="visible", timeout=timeout)
        except Exception:
            # Fall back to attached state if not visible
            await target.wait_for(state="attached", timeout=timeout)

        await target.scroll_into_view_if_needed()

        # Human-like pause before clicking
        pause_time = random.uniform(0.1, 0.3)
        await asyncio.sleep(pause_time)

        await target.click(timeout=timeout)
        logger.debug(f"Successfully clicked: {selector}")
        return True

    except Exception as e:
        logger.warning(f"Failed to click element '{selector}': {e}")
        return False


async def safe_fill(
    page: Page,
    selector: str,
    text: str,
    timeout: int = 10000,
    wait_for_timeout: Optional[int] = None,
) -> bool:
    """Safely fill text input with human-like behavior (async)"""
    try:
        locator = page.locator(selector)

        if wait_for_timeout is not None:
            try:
                await locator.wait_for(state="attached", timeout=wait_for_timeout)
            except Exception:
                return False

        element_count = await locator.count()

        if element_count == 0:
            logger.warning(f"No elements found for selector: {selector}")
            return False

        # Select the first matched element (even if multiple)
        target = locator.first if element_count > 1 else locator

        if element_count > 1:
            logger.debug(
                f"Found {element_count} elements for selector '{selector}', using the first match"
            )

        # Ensure visibility and bring into view
        try:
            await target.wait_for(state="visible", timeout=timeout)
        except Exception:
            # Fall back to attached state if not visible
            await target.wait_for(state="attached", timeout=timeout)

        await target.scroll_into_view_if_needed()

        # Clear then fill
        try:
            await target.clear()
        except Exception:
            pass

        pause(1, 2)

        await target.fill(text)

        logger.debug(f"Successfully filled '{selector}' with text {text}")
        return True

    except Exception as e:
        logger.warning(f"Failed to fill element '{selector}': {e}")
        return False


async def get_element_text(page: Page, selector: str, timeout: int = 5000) -> Optional[str]:
    """Get text content from element (async)"""
    try:
        locator = page.locator(selector)
        if await locator.count() == 0:
            return None

        await locator.wait_for(state="visible", timeout=timeout)
        text = await locator.text_content()
        if text:
            text = re.sub(r"\s+", " ", text).strip()
        else:
            text = None
        return text

    except Exception as e:
        logger.warning(f"Failed to get text from '{selector}': {e}")
        return None


async def get_clean_text(element):
    """Extract clean text from element, targeting the actual text span (async)"""
    try:
        # Try to find the specific span with text content first
        if hasattr(element, "locator"):
            text_locator = element.locator("span.text-body-small").first
            if await text_locator.count() > 0:
                text = await text_locator.text_content() or ""
                return text.strip()
        else:
            # Fallback for non-Playwright elements (should not happen in async context)
            text_span = element.find_element("css selector", "span.text-body-small")
            if text_span:
                return text_span.text.strip()
    except Exception:
        pass

    # Fallback to getting text from entire element and cleaning it
    try:
        if hasattr(element, "text_content"):
            if callable(element.text_content):
                raw = await element.text_content() or ""
            else:
                raw = element.text_content or ""
            text = raw.strip()
        else:
            text = element.text.strip()
    except Exception:
        text = ""
    # Remove extra whitespace and newlines
    text = re.sub(r"\s+", " ", text)
    return text


async def get_element_attribute(
    page: Page, selector: str, attribute: str, timeout: int = 5000
) -> Optional[str]:
    """Get attribute value from element (async)"""
    try:
        locator = page.locator(selector)
        if await locator.count() == 0:
            return None

        await locator.wait_for(state="attached", timeout=timeout)
        return await locator.get_attribute(attribute)

    except Exception as e:
        logger.warning(f"Failed to get attribute '{attribute}' from '{selector}': {e}")
        return None


# Utility function to pause execution (keep from original utils)
def pause(low: float = 0.5, high: float = 1) -> None:
    """Hold a random pause between low and high seconds"""
    pause_time = round(random.uniform(low, high), 1)
    time.sleep(pause_time)


async def find_element_safely(
    page: Page, selector: str, by: str = "css selector", timeout: Optional[int] = None
):
    """Find element using optimal method for browser type (async)"""
    try:
        # Normalize selector for Playwright
        final_selector = (
            selector if by == "css selector" else f"xpath={selector}" if by == "xpath" else selector
        )
        element = page.locator(final_selector).first

        if timeout is not None:
            try:
                await element.wait_for(state="attached", timeout=timeout)
            except Exception:
                return None

        if await element.count() > 0:
            return element
        else:
            return None
    except Exception as e:
        logger.debug(f"Element finding failed for '{selector}': {e}")
        return None


async def find_elements_safely(
    page: Page, selector: str, by: str = "css selector", timeout: Optional[int] = None
) -> List[Any]:
    """Find elements using optimal method for browser type (async)"""
    try:
        final_selector = (
            selector if by == "css selector" else f"xpath={selector}" if by == "xpath" else selector
        )
        elements = await page.locator(final_selector).all()

        if timeout is not None:
            try:
                await elements.wait_for(state="attached", timeout=timeout)
            except Exception:
                return []

        if len(elements) > 0:
            return elements
        else:
            return []

    except Exception as e:
        logger.debug(f"Elements finding failed for '{selector}': {e}")
        return []


async def send_keys_to_element(page: Page, element: Any, keys: str) -> bool:
    """Send keys to element with framework compatibility (async)"""
    try:
        if keys == "Enter":
            # Handle Enter key specifically
            await page.keyboard.press("Enter")
        else:
            try:
                # Prefer locator typing when available
                if hasattr(element, "fill"):
                    try:
                        # best-effort to clear then type
                        await element.fill(str(keys))
                    except Exception:
                        await element.type(str(keys))
                else:
                    await page.keyboard.type(str(keys))
            except Exception:
                await page.keyboard.type(str(keys))
        return True
    except Exception as e:
        logger.warning(f"Failed to send keys: {e}")
        return False


async def get_element_attribute_safely(
    element: Any, selector: str, attribute: str, by: str = "css selector"
) -> str:
    """Get element attribute using optimal method for browser type (async)"""
    try:
        # Handle Playwright Locator objects
        if hasattr(element, "evaluate"):
            # Direct Playwright Locator - find child element
            child_locator = element.locator(selector)
            if await child_locator.count() > 0:
                return await child_locator.get_attribute(attribute) or ""
        elif hasattr(element, "locator"):
            # Element wrapper - get locator and find child
            if callable(element.locator):
                locator = element.locator()
            else:
                locator = element.locator
            child_locator = locator.locator(selector)
            if await child_locator.count() > 0:
                return await child_locator.get_attribute(attribute) or ""
        return ""
    except Exception as e:
        logger.debug(f"Failed to get attribute {attribute} from element {selector}: {e}")
        return ""


async def is_scrollable(element) -> bool:
    """
    Check if an element is scrollable (Playwright compatible) - async

    Works with:
    - PlaywrightElementWrapper
    - Playwright Locator objects
    - Page elements

    Args:
        element: Element to check for scrollability

    Returns:
        bool: True if element is scrollable vertically or horizontally
    """
    try:
        # Handle different element types
        if hasattr(element, "evaluate"):
            # Direct Playwright Locator - use it directly
            locator = element
        elif hasattr(element, "locator") and not callable(element.locator):
            # PlaywrightElementWrapper with locator property
            locator = element.locator
        else:
            logger.warning(f"Unsupported element type for scrollability check: {type(element)}")
            return False

        # Use JavaScript to get scroll properties directly from DOM
        is_scrollable_result = await locator.evaluate(
            """
            (element) => {
                const verticalScrollable = element.scrollHeight > element.clientHeight;
                const horizontalScrollable = element.scrollWidth > element.clientWidth;
                return verticalScrollable || horizontalScrollable;
            }
        """
        )

        return bool(is_scrollable_result)

    except Exception as e:
        logger.warning(f"Error checking if element is scrollable: {e}")
        return False


async def scroll_slowly(
    locator: Any, direction: str = "down", time_to_scroll_sec: float = 1.5, delay: float = 0.01
) -> bool:
    """
    Scroll an element in the specified direction (Playwright compatible) - async

    Args:
        locator: Element to scroll (PlaywrightElementWrapper or Playwright Locator)
        direction: "down", "up"
        time_to_scroll_sec: Total time to spend scrolling
        delay: Delay between scroll steps

    Returns:
        bool: True if scrolling was successful, False otherwise
    """
    try:
        scroll_height = await locator.evaluate("(element) => element.scrollHeight")
        client_height = await locator.evaluate("(element) => element.clientHeight")
        distance = scroll_height - client_height

        # If there's no scrollable content, return early
        if distance <= 10:
            logger.debug("Element has no scrollable content or distance is too short")
            return False
        else:
            distance += 300

        # Calculate number of steps and step size
        total_steps = int(time_to_scroll_sec / delay)
        step_size = int(distance / total_steps) if total_steps > 0 else distance

        logger.debug(
            f"Scrolling {direction}: distance={distance}, steps={total_steps}, step_size={step_size:.2f}"
        )

        # Get current scroll position
        current_scroll = await locator.evaluate("(element) => element.scrollTop")

        for i in range(total_steps + 1):
            if direction == "down":
                target_scroll = current_scroll + (step_size * i)
                # Don't scroll beyond the maximum
                target_scroll = min(target_scroll, distance)
            elif direction == "up":
                target_scroll = current_scroll - (step_size * i)
                # Don't scroll above 0
                target_scroll = max(target_scroll, 0)
            else:
                logger.warning(f"Unsupported scroll direction: {direction}")
                return False

            # Apply the scroll
            await locator.evaluate(f"(element) => {{ element.scrollTop = {target_scroll}; }}")
            await asyncio.sleep(delay)

        return True

    except Exception as e:
        logger.warning(f"Error scrolling element {direction}: {e}")
        return False
