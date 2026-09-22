"""
DocStudio Browser Visual Provider — Meta AI Automation Adapter.
Connects the real Chromium BrowserAutomationDriver to Meta AI (https://www.meta.ai).
Uses Meta AI's high-speed image synthesis (Imagine), then animates with DocStudio's
hardware-accelerated Ken Burns motion engine and 35mm documentary color grading.
Adheres strictly to the authentication rule: never hardcodes credentials.
Uses persistent user profile created via LAUNCH_META_AI.bat.
"""

from __future__ import annotations
import logging
import time
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional

from docstudio.visual_providers.browser.driver import BrowserAutomationDriver
from docstudio.motion import get_ken_burns_filter

logger = logging.getLogger("docstudio.browser.meta_ai")

DEFAULT_META_PROFILE_DIR = Path("cache/browser_profiles/meta_ai")
DEFAULT_META_URL = "https://www.meta.ai"


class MetaAIAdapter:
    """
    Adapter controlling Meta AI via real Chromium automation.
    Fast image synthesis + pipeline motion animation.
    """

    def __init__(
        self,
        driver: Optional[BrowserAutomationDriver] = None,
        profile_dir: Optional[str | Path] = None,
        headless: bool = True,
        timeout_seconds: int = 60,
    ):
        self.profile_dir = Path(profile_dir) if profile_dir else DEFAULT_META_PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.timeout_seconds = timeout_seconds

        self.driver = driver or BrowserAutomationDriver(
            headless=self.headless,
            user_data_dir=self.profile_dir,
            timeout_ms=30000,
        )

    def open_meta_ai(self) -> bool:
        """Launches Chromium and navigates to Meta AI."""
        if not self.driver.is_active:
            if not self.driver.launch():
                logger.error("[MetaAI] Failed to launch Chromium browser.")
                return False

        logger.info(f"[MetaAI] Opening Meta AI: {DEFAULT_META_URL}")
        nav_ok = self.driver.open_url(DEFAULT_META_URL, wait_until="domcontentloaded")
        if not nav_ok:
            logger.error("[MetaAI] Failed to load Meta AI URL.")
            return False

        try:
            self.driver.page.wait_for_timeout(3000)
        except Exception:
            pass

        return True

    def check_auth_state(self) -> Dict[str, Any]:
        """
        Determines if the user has an active authenticated Meta AI session.
        """
        if not self.driver.is_active:
            if not self.open_meta_ai():
                return {"authenticated": False, "error": "Browser failed to launch"}

        page = self.driver.page
        url = page.url
        title = page.title()

        # Check for prompt input or user profile indicator
        has_prompt = False
        selectors = [
            "[contenteditable='true']",
            "textarea[placeholder*='Ask' i]",
            "textarea[placeholder*='imagine' i]",
            "textarea",
        ]
        for sel in selectors:
            try:
                if page.locator(sel).first.is_visible(timeout=1500):
                    has_prompt = True
                    break
            except Exception:
                continue

        login_indicators = [
            "button:has-text('Log in')",
            "button:has-text('Sign in')",
            "a[href*='login']",
        ]
        login_required = False
        for sel in login_indicators:
            try:
                if page.locator(sel).first.is_visible(timeout=1000):
                    login_required = True
                    break
            except Exception:
                continue

        is_auth = has_prompt and not login_required
        return {
            "authenticated": is_auth,
            "current_url": url,
            "page_title": title,
            "login_required": login_required,
        }

    def generate_image(self, prompt: str, output_path: Path) -> Optional[Path]:
        """
        Generates a high-resolution still image using Meta AI's 'Imagine' engine.
        Returns the downloaded image Path if successful.
        """
        if not self.driver.is_active:
            if not self.open_meta_ai():
                return None

        page = self.driver.page
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare image URL interceptor
        captured_images = []
        def on_response(response):
            try:
                url = response.url
                ct = response.headers.get("content-type", "").lower()
                if ("image/" in ct or any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"])) and "fbcdn.net" in url:
                    if not any(icon in url.lower() for icon in ["rsrc.php", "emoji", "orbit.png", "logo", "favicon", "profile"]):
                        captured_images.append(url)
            except Exception:
                pass

        page.on("response", on_response)

        # Find prompt element
        selectors = [
            "[contenteditable='true']",
            "textarea[placeholder*='Ask' i]",
            "textarea[placeholder*='imagine' i]",
            "textarea",
            "input[type='text']",
        ]
        prompt_loc = None
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=2000):
                    prompt_loc = loc
                    break
            except Exception:
                continue

        if not prompt_loc:
            logger.error("[MetaAI] Prompt field not visible.")
            return None

        # Format prompt with 'Imagine' keyword if not already present
        meta_prompt = prompt.strip()
        if not meta_prompt.lower().startswith("imagine"):
            meta_prompt = f"Imagine {meta_prompt}"

        logger.info(f"[MetaAI] Submitting image prompt: {meta_prompt[:70]}...")
        prompt_loc.fill(meta_prompt)
        page.wait_for_timeout(300)
        prompt_loc.press("Enter")

        # Wait for image generation (typically 5-20 seconds)
        start_t = time.time()
        found_url = None

        while time.time() - start_t < self.timeout_seconds:
            # Check DOM for image tags
            try:
                imgs = page.locator("img[src*='fbcdn.net']").all()
                for img in imgs:
                    src = img.get_attribute("src")
                    if src and not any(k in src.lower() for k in ["rsrc.php", "profile", "emoji", "orbit"]):
                        found_url = src
                        break
                if found_url:
                    break
            except Exception:
                pass

            if captured_images:
                found_url = captured_images[-1]
                break

            time.sleep(1)

        if not found_url and captured_images:
            found_url = captured_images[-1]

        if not found_url:
            logger.warning("[MetaAI] No image URL detected within timeout.")
            return None

        # Download image
        try:
            logger.info(f"[MetaAI] Downloading generated image: {found_url[:80]}...")
            resp = requests.get(found_url, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"[MetaAI] Saved image to {output_path} ({len(resp.content)} bytes)")
                return output_path
        except Exception as exc:
            logger.error(f"[MetaAI] Image download error: {exc}")

        return None

    def generate_video_clip(
        self,
        prompt: str,
        duration: float,
        motion_type: str = "zoom_in",
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Generates an image via Meta AI, then immediately animates it into a production-ready MP4
        clip using hardware-accelerated Ken Burns motion and documentary color grading.
        """
        out_mp4 = Path(output_path) if output_path else Path(f"cache/visuals/meta_ai_{int(time.time())}.mp4")
        out_mp4.parent.mkdir(parents=True, exist_ok=True)

        temp_img = out_mp4.with_suffix(".jpg")
        img_ok = self.generate_image(prompt, temp_img)
        if not img_ok or not temp_img.exists():
            logger.error("[MetaAI] Failed to generate source image for animation.")
            return None

        # Animate with FFmpeg Ken Burns filter
        vf = get_ken_burns_filter(
            motion_type=motion_type,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(temp_img),
            "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(out_mp4),
        ]

        logger.info(f"[MetaAI] Animating image into video cut ({duration}s, {motion_type})...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and out_mp4.exists() and out_mp4.stat().st_size > 5000:
            logger.info(f"[MetaAI] Successfully created animated video clip: {out_mp4} ({out_mp4.stat().st_size} bytes)")
            return out_mp4
        else:
            logger.error(f"[MetaAI] FFmpeg animation failed: {res.stderr[-300:]}")
            return None

    def close(self):
        """Closes browser session."""
        if self.driver:
            self.driver.close()
