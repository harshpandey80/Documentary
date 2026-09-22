"""
DocStudio Browser Visual Provider — Google Flow Automation Adapter.
Connects the real Chromium BrowserAutomationDriver to Google Flow (flow.google.com).
Adheres strictly to the authentication rule: never automates Google credentials or bypasses CAPTCHA.
Requires one-time interactive login via persistent browser profile.
"""

from __future__ import annotations
import logging
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from docstudio.visual_providers.browser.driver import BrowserAutomationDriver

logger = logging.getLogger("docstudio.browser.google_flow")

DEFAULT_FLOW_PROFILE_DIR = Path("cache/browser_profiles/google_flow")
DEFAULT_FLOW_URL = "https://flow.google.com"


class GoogleFlowAdapter:
    """
    Adapter controlling Google Flow via real Chromium automation.
    Manages session detection, prompt submission, progress polling, and video asset retrieval.
    """

    def __init__(
        self,
        driver: Optional[BrowserAutomationDriver] = None,
        profile_dir: Optional[str | Path] = None,
        headless: bool = True,
        timeout_seconds: int = 180,
    ):
        self.profile_dir = Path(profile_dir) if profile_dir else DEFAULT_FLOW_PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.timeout_seconds = timeout_seconds

        self.driver = driver or BrowserAutomationDriver(
            headless=self.headless,
            user_data_dir=self.profile_dir,
            timeout_ms=30000,
        )

    def open_flow(self) -> bool:
        """Launches Chromium and navigates to Google Flow."""
        if not self.driver.is_active:
            if not self.driver.launch():
                logger.error("[GoogleFlow] Failed to launch Chromium browser.")
                return False

        logger.info(f"[GoogleFlow] Opening Google Flow: {DEFAULT_FLOW_URL}")
        nav_ok = self.driver.open_url(DEFAULT_FLOW_URL, wait_until="domcontentloaded")
        if not nav_ok:
            logger.error("[GoogleFlow] Failed to load Google Flow URL.")
            return False

        # Wait briefly for client-side redirection or session hydration
        try:
            self.driver.page.wait_for_timeout(2500)
        except Exception:
            pass

        return True

    def check_auth_state(self) -> Dict[str, Any]:
        """
        Determines if the user has an active authenticated Google session.
        Returns:
            {"authenticated": bool, "current_url": str, "page_title": str, "login_required": bool}
        """
        if not self.driver.is_active:
            return {
                "authenticated": False,
                "current_url": "",
                "page_title": "",
                "login_required": True,
                "reason": "Browser not active",
            }

        url = self.driver.get_url()
        title = self.driver.get_title()

        # 1. Direct Google Accounts sign-in detection
        if "accounts.google.com" in url or "Sign in - Google Accounts" in title:
            return {
                "authenticated": False,
                "current_url": url,
                "page_title": title,
                "login_required": True,
                "reason": "Redirected to Google Accounts login screen.",
            }

        # 2. Check for public landing page / sign-in callouts
        if "flow.google.com/about" in url or "about" in url:
            # Landing page: check if "Create with Google Flow" button triggers login redirect
            try:
                sign_in_el = self.driver.page.locator("a:has-text('Sign in'), button:has-text('Sign in'), a:has-text('Log in')").first
                if sign_in_el.is_visible():
                    return {
                        "authenticated": False,
                        "current_url": url,
                        "page_title": title,
                        "login_required": True,
                        "reason": "Public marketing landing page detected with unauthenticated state.",
                    }
            except Exception:
                pass

        # 3. Check for authenticated UI markers (e.g. prompt bar, user avatar, project studio)
        has_prompt_input = False
        try:
            prompt_locator = self.driver.page.locator(
                "textarea, [contenteditable='true'], input[placeholder*='prompt' i], [aria-label*='prompt' i]"
            ).first
            has_prompt_input = prompt_locator.is_visible(timeout=3000)
        except Exception:
            has_prompt_input = False

        if has_prompt_input:
            return {
                "authenticated": True,
                "current_url": url,
                "page_title": title,
                "login_required": False,
                "reason": "Authenticated studio prompt interface detected.",
            }

        # If not on accounts.google.com but also prompt not immediately visible,
        # test clicking 'Create with Google Flow' to see if it redirects to login
        try:
            create_btn = self.driver.page.locator("button:has-text('Create with Google Flow'), a:has-text('Create with Google Flow')").first
            if create_btn.is_visible(timeout=2000):
                create_btn.click()
                self.driver.page.wait_for_timeout(2500)
                new_url = self.driver.get_url()
                new_title = self.driver.get_title()
                if "accounts.google.com" in new_url or "Sign in" in new_title:
                    return {
                        "authenticated": False,
                        "current_url": new_url,
                        "page_title": new_title,
                        "login_required": True,
                        "reason": "Action triggered Google Accounts login redirect.",
                    }
        except Exception:
            pass

        # Default fallback assessment
        is_auth = "accounts.google.com" not in self.driver.get_url() and not ("about" in self.driver.get_url())
        return {
            "authenticated": is_auth,
            "current_url": self.driver.get_url(),
            "page_title": self.driver.get_title(),
            "login_required": not is_auth,
            "reason": "Session state derived from URL hierarchy.",
        }

    def generate_video(
        self,
        prompt: str,
        output_path: str | Path,
        screenshot_dir: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """
        Executes single video generation on Google Flow:
        1. Opens Flow.
        2. Detects authentication. If not logged in, halts safely and alerts user.
        3. Enters prompt and clicks generate.
        4. Polls generation output.
        5. Downloads and validates resulting MP4.
        """
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        diag_dir = Path(screenshot_dir) if screenshot_dir else out_p.parent / "diagnostics"
        diag_dir.mkdir(parents=True, exist_ok=True)

        if not self.open_flow():
            return {
                "status": "failed",
                "stage": "navigation",
                "message": "Failed to navigate to Google Flow.",
                "asset_path": None,
            }

        # Step 2: Detect Auth
        auth_state = self.check_auth_state()
        logger.info(f"[GoogleFlow] Auth Check: {auth_state}")

        if auth_state.get("login_required", False) or not auth_state.get("authenticated", False):
            screenshot_path = diag_dir / "google_flow_auth_required.png"
            self.driver.take_screenshot(screenshot_path)
            return {
                "status": "auth_required",
                "stage": "authentication",
                "message": "Manual Google login required. Please log in through the browser and rerun the test.",
                "current_url": auth_state.get("current_url"),
                "page_title": auth_state.get("page_title"),
                "screenshot": str(screenshot_path),
                "asset_path": None,
            }

        # Step 3: Locate Prompt Input
        prompt_locator = None
        selectors = [
            "textarea[placeholder*='prompt' i]",
            "textarea[aria-label*='prompt' i]",
            "textarea",
            "[contenteditable='true']",
            "input[placeholder*='prompt' i]",
        ]
        for sel in selectors:
            try:
                loc = self.driver.page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    prompt_locator = loc
                    break
            except Exception:
                continue

        if not prompt_locator:
            screenshot_path = diag_dir / "google_flow_missing_prompt.png"
            self.driver.take_screenshot(screenshot_path)
            return {
                "status": "ui_selector_unresolved",
                "stage": "prompt_input",
                "message": "Could not locate Google Flow prompt input element.",
                "current_url": self.driver.get_url(),
                "page_title": self.driver.get_title(),
                "screenshot": str(screenshot_path),
                "asset_path": None,
            }

        # Step 4: Fill Prompt
        logger.info(f"[GoogleFlow] Submitting prompt: {prompt}")
        prompt_locator.fill(prompt)

        # Step 5: Submit Generation
        submit_btn = None
        submit_selectors = [
            "button[aria-label*='Generate' i]",
            "button:has-text('Generate')",
            "button:has-text('Create')",
            "button[type='submit']",
            "[data-testid*='generate']",
        ]
        for ssel in submit_selectors:
            try:
                btn = self.driver.page.locator(ssel).first
                if btn.is_visible(timeout=2000) and btn.is_enabled():
                    submit_btn = btn
                    break
            except Exception:
                continue

        if not submit_btn:
            # Try Enter key on prompt element
            prompt_locator.press("Enter")
        else:
            submit_btn.click()

        # Step 6: Wait for Video Generation Completion
        logger.info("[GoogleFlow] Generation initiated. Waiting for output video...")
        start_time = time.time()
        video_locator = None

        while time.time() - start_time < self.timeout_seconds:
            try:
                # Look for rendered video tag
                videos = self.driver.page.locator("video").all()
                for v in videos:
                    src = v.get_attribute("src")
                    if src and not src.startswith("blob:http://localhost"):
                        video_locator = v
                        break
                if video_locator:
                    break
            except Exception:
                pass
            time.sleep(3)

        if not video_locator:
            screenshot_path = diag_dir / "google_flow_generation_timeout.png"
            self.driver.take_screenshot(screenshot_path)
            return {
                "status": "timeout",
                "stage": "generation_wait",
                "message": f"Generation did not complete within {self.timeout_seconds} seconds.",
                "screenshot": str(screenshot_path),
                "asset_path": None,
            }

        # Step 7: Download / Save Asset
        video_src = video_locator.get_attribute("src")
        if video_src:
            import requests
            resp = requests.get(video_src, stream=True, timeout=60)
            if resp.status_code == 200:
                with open(out_p, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=16384):
                        f.write(chunk)

        # Step 8: Validate with FFprobe
        dur = self._verify_video_file(out_p)
        if dur > 0:
            return {
                "status": "success",
                "stage": "completed",
                "asset_path": str(out_p),
                "duration": dur,
                "message": f"Video generated and validated successfully ({dur:.2f}s).",
            }
        else:
            return {
                "status": "invalid_asset",
                "stage": "asset_verification",
                "asset_path": str(out_p) if out_p.exists() else None,
                "message": "Downloaded video could not be validated with ffprobe.",
            }

    @staticmethod
    def _verify_video_file(file_path: Path) -> float:
        """Returns video duration via ffprobe or 0.0 if invalid."""
        if not file_path.exists() or file_path.stat().st_size < 5000:
            return 0.0
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json", str(file_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                return float(data.get("format", {}).get("duration", 0.0))
        except Exception:
            pass
        return 0.0

    def close(self) -> None:
        """Closes browser session."""
        self.driver.close()
