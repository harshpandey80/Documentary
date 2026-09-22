"""
DocStudio AI Video Provider — Meta AI Image Synthesis + Pipeline Motion Animation.
Converts Meta AI photorealistic still images into dynamic documentary cuts using
DocStudio's hardware-accelerated Ken Burns motion engine and 35mm documentary color grading.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from docstudio.ai_video.base_provider import AIVideoProvider, VideoGenerationResult
from docstudio.visual_providers.browser.meta_ai import MetaAIAdapter, DEFAULT_META_PROFILE_DIR

logger = logging.getLogger("docstudio.ai_video.meta_ai")


class MetaAIVideoProvider(AIVideoProvider):
    """
    Combines high-speed Meta AI image synthesis (Imagine) with pipeline
    camera motion (zoom_in, zoom_out, pan_left, pan_right, zoom_punch).
    """

    def __init__(self, profile_dir: Optional[Path] = None, headless: bool = True):
        self.profile_dir = Path(profile_dir) if profile_dir else DEFAULT_META_PROFILE_DIR
        self.headless = headless

    def is_available(self) -> bool:
        # Available if the authenticated profile directory exists
        return self.profile_dir.exists()

    def generate_video(
        self,
        prompt: str,
        duration: float = 4.0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        motion_type: str = "zoom_in",
        output_path: Optional[Path | str] = None,
    ) -> VideoGenerationResult:
        out_p = Path(output_path) if output_path else Path(f"cache/visuals/meta_ai_{int(duration)}s.mp4")
        out_p.parent.mkdir(parents=True, exist_ok=True)

        try:
            adapter = MetaAIAdapter(profile_dir=self.profile_dir, headless=self.headless)
            # Check auth state first — fast fail before slow browser ops
            if not adapter.open_meta_ai():
                logger.error("[MetaAIVideoProvider] Browser failed to open meta.ai — falling through to next provider.")
                return VideoGenerationResult(
                    status="failed", video_path=None, duration=duration,
                    provider="meta_ai", model="meta-imagine-kenburns",
                    metadata={"error": "Browser could not open meta.ai"},
                )
            auth = adapter.check_auth_state()
            if not auth.get("authenticated"):
                reason = "login_required" if auth.get("login_required") else auth.get("error", "unknown")
                logger.warning(f"[MetaAIVideoProvider] Meta AI not authenticated ({reason}). Run LAUNCH_META_AI.bat and log in first.")
                adapter.close()
                return VideoGenerationResult(
                    status="failed", video_path=None, duration=duration,
                    provider="meta_ai", model="meta-imagine-kenburns",
                    metadata={"error": f"Not authenticated: {reason}"},
                )
            rendered = adapter.generate_video_clip(
                prompt=prompt,
                duration=duration,
                motion_type=motion_type,
                width=width,
                height=height,
                fps=fps,
                output_path=out_p,
            )
            adapter.close()
            if rendered and rendered.exists() and rendered.stat().st_size > 5000:
                return VideoGenerationResult(
                    status="success",
                    video_path=str(rendered),
                    duration=duration,
                    provider="meta_ai",
                    model="meta-imagine-kenburns",
                    metadata={"width": width, "height": height, "fps": fps, "motion": motion_type},
                )
            else:
                logger.error(f"[MetaAIVideoProvider] Clip generated but empty/missing: {out_p}")
        except Exception as exc:
            logger.error(f"[MetaAIVideoProvider] Generation error: {exc}", exc_info=True)

        return VideoGenerationResult(
            status="failed",
            video_path=None,
            duration=duration,
            provider="meta_ai",
            model="meta-imagine-kenburns",
            metadata={"error": "Generation failed"},
        )
