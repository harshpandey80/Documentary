"""
DocStudio Browser Visual Provider — Real Chromium Automation Driver.
Provides lightweight, reliable browser automation for web-based generation workflows.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger("docstudio.browser.driver")


class BrowserAutomationDriver:
    """
    Lightweight automation controller for Chromium-based browsers via Playwright.
    Provides fundamental browser operations: launch, navigate, query, interact, screenshot, and cleanup.
    Supports persistent user data directory for retained authentication sessions.
    """

    def __init__(
        self,
        headless: bool = True,
        preferred_channel: Optional[str] = "chrome",
        timeout_ms: int = 30000,
        user_data_dir: Optional[str | Path] = None,
    ):
        self.headless = headless
        self.preferred_channel = preferred_channel
        self.timeout_ms = timeout_ms
        self.user_data_dir = Path(user_data_dir) if user_data_dir else None

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    @property
    def page(self) -> Any:
        """Direct access to underlying Playwright page."""
        return self._page

    @property
    def context(self) -> Any:
        """Direct access to underlying Playwright browser context."""
        return self._context

    @property
    def is_active(self) -> bool:
        """Returns True if the browser/context and page are open and responsive."""
        context_active = self._context is not None or self._browser is not None
        return context_active and self._page is not None and not self._page.is_closed()

    def launch(self) -> bool:
        """
        Launches real Chromium process.
        Attempts preferred channel (e.g. system Chrome or Edge) before falling back to bundled Chromium.
        If user_data_dir is set, launches a persistent context for saved sessions/cookies.
        """
        if self.is_active:
            logger.debug("Browser is already launched and active.")
            return True

        try:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()

            launch_attempts = []
            if self.preferred_channel:
                launch_attempts.append({"channel": self.preferred_channel})
            # Common fallbacks
            if self.preferred_channel != "chrome":
                launch_attempts.append({"channel": "chrome"})
            if self.preferred_channel != "msedge":
                launch_attempts.append({"channel": "msedge"})
            launch_attempts.append({})  # Default bundled Chromium

            launched = False
            last_err = None

            for opts in launch_attempts:
                try:
                    logger.info(f"[BrowserDriver] Launching Chromium (channel={opts.get('channel', 'bundled')}, headless={self.headless}, profile={self.user_data_dir})")
                    if self.user_data_dir:
                        self.user_data_dir.mkdir(parents=True, exist_ok=True)
                        self._context = self._playwright.chromium.launch_persistent_context(
                            user_data_dir=str(self.user_data_dir),
                            headless=self.headless,
                            timeout=self.timeout_ms,
                            viewport={"width": 1280, "height": 720},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                            **opts,
                        )
                        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
                    else:
                        self._browser = self._playwright.chromium.launch(
                            headless=self.headless,
                            timeout=self.timeout_ms,
                            **opts,
                        )
                        self._context = self._browser.new_context(
                            viewport={"width": 1280, "height": 720},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                        )
                        self._page = self._context.new_page()

                    self._context.set_default_timeout(self.timeout_ms)
                    launched = True
                    break
                except Exception as exc:
                    last_err = exc
                    logger.debug(f"[BrowserDriver] Launch attempt failed ({opts}): {exc}")

            if not launched or self._page is None:
                raise RuntimeError(f"Failed to launch Chromium browser: {last_err}")

            logger.info("[BrowserDriver] Chromium session initialized successfully.")
            return True

        except Exception as exc:
            logger.error(f"[BrowserDriver] Launch failed: {exc}")
            self.close()
            return False

    def open_url(self, url: str, wait_until: str = "load") -> bool:
        """Navigates to the specified URL."""
        if not self.is_active:
            if not self.launch():
                return False

        try:
            logger.info(f"[BrowserDriver] Navigating to: {url}")
            self._page.goto(url, wait_until=wait_until, timeout=self.timeout_ms)
            return True
        except Exception as exc:
            logger.error(f"[BrowserDriver] Failed to navigate to {url}: {exc}")
            return False

    def get_url(self) -> str:
        """Returns the current page URL."""
        if not self.is_active or self._page is None:
            return ""
        return self._page.url

    def get_title(self) -> str:
        """Returns the current page title."""
        if not self.is_active or self._page is None:
            return ""
        return self._page.title()

    def fill_text(self, selector: str, text: str) -> bool:
        """Fills an input or textarea element matched by selector."""
        if not self.is_active or self._page is None:
            return False
        try:
            self._page.fill(selector, text, timeout=self.timeout_ms)
            return True
        except Exception as exc:
            logger.error(f"[BrowserDriver] Failed to fill text at '{selector}': {exc}")
            return False

    def click_element(self, selector: str) -> bool:
        """Clicks an element matched by selector."""
        if not self.is_active or self._page is None:
            return False
        try:
            self._page.click(selector, timeout=self.timeout_ms)
            return True
        except Exception as exc:
            logger.error(f"[BrowserDriver] Failed to click element at '{selector}': {exc}")
            return False

    def wait_for_selector(self, selector: str, timeout_ms: Optional[int] = None) -> bool:
        """Waits for an element matching selector to appear in the DOM."""
        if not self.is_active or self._page is None:
            return False
        try:
            t = timeout_ms or self.timeout_ms
            self._page.wait_for_selector(selector, timeout=t)
            return True
        except Exception as exc:
            logger.error(f"[BrowserDriver] Selector '{selector}' not found within {t}ms: {exc}")
            return False

    def take_screenshot(self, output_path: str | Path, full_page: bool = False) -> Optional[Path]:
        """Captures a screenshot of the current page and saves to output_path."""
        if not self.is_active or self._page is None:
            logger.error("[BrowserDriver] Cannot take screenshot: browser not active.")
            return None
        try:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(out), full_page=full_page)
            logger.info(f"[BrowserDriver] Screenshot saved: {out} ({out.stat().st_size} bytes)")
            return out
        except Exception as exc:
            logger.error(f"[BrowserDriver] Screenshot capture failed: {exc}")
            return None

    def close(self) -> None:
        """Cleanly terminates page, browser context, and Playwright driver process."""
        try:
            if self._page and not self._page.is_closed():
                self._page.close()
        except Exception:
            pass
        finally:
            self._page = None

        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        finally:
            self._context = None

        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        finally:
            self._browser = None

        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        finally:
            self._playwright = None

        logger.info("[BrowserDriver] Browser closed cleanly.")

    def __enter__(self) -> BrowserAutomationDriver:
        self.launch()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
