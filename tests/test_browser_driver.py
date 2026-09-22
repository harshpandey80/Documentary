"""
Smoke test for BrowserAutomationDriver with real Chromium.
Verifies launching real Chromium, navigating to https://example.com, reading page title,
capturing a screenshot, and clean shutdown.
"""

import pytest
from pathlib import Path
from docstudio.visual_providers.browser.driver import BrowserAutomationDriver


def test_real_chromium_navigation_and_screenshot(tmp_path: Path):
    driver = BrowserAutomationDriver(headless=True)
    screenshot_file = tmp_path / "example_com.png"

    try:
        # 1. Launch real Chromium
        launched = driver.launch()
        assert launched is True, "Failed to launch real Chromium process"
        assert driver.is_active is True

        # 2. Navigate to https://example.com
        nav_ok = driver.open_url("https://example.com")
        assert nav_ok is True, "Failed to navigate to https://example.com"

        # 3. Read page title and URL
        title = driver.get_title()
        url = driver.get_url()
        assert "example" in title.lower() or "example" in url.lower(), f"Unexpected title/url: {title} ({url})"

        # 4. Produce a screenshot
        saved = driver.take_screenshot(screenshot_file)
        assert saved is not None
        assert screenshot_file.exists()
        assert screenshot_file.stat().st_size > 1000, f"Screenshot too small: {screenshot_file.stat().st_size} bytes"

    finally:
        # 5. Close cleanly
        driver.close()
        assert driver.is_active is False
