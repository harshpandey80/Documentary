"""
DocStudio Browser Visual Provider — Web Creative Generation Implementation.
Implements browser-based generation with DOM/semantic interaction, queue concurrency,
screenshot diagnostics, and automatic fallback to cloud/local generators.
"""

from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

from docstudio.visual_providers.browser.base_provider import (
    BrowserVisualProvider,
    BrowserGenerationResponse,
)
from docstudio.visual_providers.browser.queue import BrowserGenerationQueue
from docstudio.remote_creative_director.manifest_schema import ShotDirective
from docstudio.remote_creative_director.browser_bridge import BrowserBridge, BrowserGenerationRequest


class WebCreativeVisualProvider(BrowserVisualProvider):
    """
    Browser-based creative visual generation provider.
    Interacts with web creative platforms without loading large weights locally.
    """

    def __init__(self, name: str = "browser_flow", max_concurrency: int = 1):
        super().__init__(name=name)
        self.queue = BrowserGenerationQueue(max_concurrency=max_concurrency)
        self._is_headless = os.getenv("DOCSTUDIO_BROWSER_HEADLESS", "true").lower() == "true"

    def is_available(self) -> bool:
        # Browser provider is available if web access is functional
        return True

    def generate_image(self, request: BrowserGenerationRequest) -> BrowserGenerationResponse:
        task = self.queue.enqueue(request.shot_id, request.to_dict())
        return BrowserGenerationResponse(
            status="pending",
            task_id=task.task_id,
            provider_name=self.name,
            metadata=request.to_dict(),
        )

    def generate_video(self, request: BrowserGenerationRequest) -> BrowserGenerationResponse:
        task = self.queue.enqueue(request.shot_id, request.to_dict())
        return BrowserGenerationResponse(
            status="pending",
            task_id=task.task_id,
            provider_name=self.name,
            metadata=request.to_dict(),
        )

    def download_asset(self, remote_url: str, dest_path: Path) -> Optional[Path]:
        dest_p = Path(dest_path)
        dest_p.parent.mkdir(parents=True, exist_ok=True)
        try:
            import requests
            resp = requests.get(remote_url, timeout=60, stream=True)
            if resp.status_code == 200:
                with open(dest_p, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return dest_p
        except Exception as exc:
            print(f"[WebProvider] Download failed for {remote_url}: {exc}")
        return None

    def generate_video_from_shot(
        self,
        shot: ShotDirective,
        topic: str,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        dest_video: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Executes generation of an AI cinematic clip for the given shot directive.
        Follows the strict fallback hierarchy if browser driver is offline.
        """
        out_p = dest_video or Path(f"cache/visuals/{shot.shot_id}.mp4")
        out_p.parent.mkdir(parents=True, exist_ok=True)

        req = BrowserBridge.create_request_from_shot(shot, width=width, height=height)
        task = self.queue.enqueue(shot.shot_id, req.to_dict())
        active_task = self.queue.acquire_next_task()

        prompt = shot.prompt or shot.visual_reason or f"Cinematic scene for {topic}"
        print(f"[WebProvider] Executing creative visual for [{shot.shot_id}]: '{prompt[:60]}...'")

        # 0. Primary: Meta AI High-Speed Image Generation + Pipeline Motion Animation
        meta_ok = False
        try:
            from docstudio.visual_providers.browser.meta_ai import MetaAIAdapter, DEFAULT_META_PROFILE_DIR
            if DEFAULT_META_PROFILE_DIR.exists():
                adapter = MetaAIAdapter(headless=self._is_headless)
                # Fast auth pre-check
                if adapter.open_meta_ai():
                    auth = adapter.check_auth_state()
                    if auth.get("authenticated"):
                        motion_type = getattr(shot, "motion", "zoom_in") or "zoom_in"
                        clip = adapter.generate_video_clip(
                            prompt=prompt,
                            duration=shot.duration,
                            motion_type=motion_type,
                            width=width,
                            height=height,
                            fps=fps,
                            output_path=out_p,
                        )
                        adapter.close()
                        if clip and clip.exists() and clip.stat().st_size > 5000:
                            meta_ok = True
                            self.queue.mark_completed(task.task_id, str(clip))
                            return clip
                        else:
                            print(f"[WebProvider] \u26a0\ufe0f Meta AI returned empty clip for [{shot.shot_id}]. Falling back to Pollinations cloud.")
                    else:
                        reason = "login_required" if auth.get("login_required") else auth.get("error", "unknown")
                        print(f"[WebProvider] \u26a0\ufe0f Meta AI not authenticated ({reason}). Run LAUNCH_META_AI.bat to log in. Falling back to cloud.")
                        adapter.close()
                else:
                    print(f"[WebProvider] \u26a0\ufe0f Meta AI browser failed to open. Falling back to cloud providers.")
            else:
                print(f"[WebProvider] Meta AI profile not found. Skipping. Run LAUNCH_META_AI.bat to set up.")
        except Exception as exc:
            print(f"[WebProvider] \u274c Meta AI error for [{shot.shot_id}]: {exc!r}. Falling back to cloud.")

        # 1. Try Pollinations Cloud Provider (Free remote generation without local weights)
        try:
            from docstudio.ai_video.providers.pollinations_provider import PollinationsVideoProvider
            prov = PollinationsVideoProvider()
            if prov.is_available():
                res = prov.generate_video(
                    prompt=prompt,
                    duration=shot.duration,
                    width=width,
                    height=height,
                    fps=fps,
                    output_path=out_p,
                )
                if res.status == "success" and res.video_path and Path(res.video_path).exists():
                    audit = BrowserBridge.audit_asset(res.video_path, expected_duration=shot.duration)
                    if audit.is_valid:
                        self.queue.mark_completed(task.task_id, str(res.video_path))
                        return Path(res.video_path)
        except Exception as exc:
            print(f"[WebProvider] Cloud synthesis notice: {exc}. Proceeding to CPU Parallax fallback.")

        # 2. Guaranteed CPU Fallback: Parallax Camera Engine
        try:
            from docstudio.ai_video.providers.parallax_provider import ParallaxCameraProvider
            parallax = ParallaxCameraProvider()
            res = parallax.generate_video(
                prompt=prompt,
                duration=shot.duration,
                width=width,
                height=height,
                fps=fps,
                output_path=out_p,
            )
            if res.video_path and Path(res.video_path).exists():
                self.queue.mark_completed(task.task_id, str(res.video_path))
                return Path(res.video_path)
        except Exception as exc:
            self.queue.mark_failed(task.task_id, str(exc))
            print(f"[WebProvider] Parallax fallback failed: {exc}")

        return None
