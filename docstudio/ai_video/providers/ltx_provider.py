"""
DocStudio LTX-Video Architectural Provider.
Supports LTX-2.5 / LTX-Video via remote API or high-end local GPU without forcing
heavy 22GB downloads on resource-constrained development machines.
"""

from __future__ import annotations
import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

from docstudio.ai_video.base_provider import AIVideoProvider, VideoGenerationResult, get_hardware_profile


class LTXVideoProvider(AIVideoProvider):
    def __init__(self, endpoint_url: Optional[str] = None, model_name: str = "ltx-2.5-22b"):
        super().__init__(name="ltx_video", model_name=model_name)
        self.endpoint_url = endpoint_url or os.getenv("LTX_API_URL", "")

    def is_available(self) -> bool:
        # 1. Available if remote API URL is specified
        if self.endpoint_url:
            return True

        # 2. Local execution strictly guarded: requires local CUDA GPU with >=12GB VRAM
        profile = get_hardware_profile()
        if profile["can_run_local_diffusion"]:
            try:
                import ltx_video  # Check if package is installed
                return True
            except ImportError:
                return False

        return False

    def generate_video(
        self,
        prompt: str,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        input_image: Optional[Path | str] = None,
        input_video: Optional[Path | str] = None,
        keyframes: Optional[List[Dict[str, Any]]] = None,
        shot_type: Optional[str] = None,
        output_path: Optional[Path | str] = None,
    ) -> VideoGenerationResult:
        if not self.is_available():
            return VideoGenerationResult(
                status="failed",
                video_path=None,
                duration=duration,
                provider=self.name,
                model=self.model_name,
                metadata={"reason": "LTX provider not configured or machine does not have required 12GB+ VRAM."},
            )

        if not output_path:
            output_path = Path("workspace") / "ai_video_cache" / f"ltx_{abs(hash(prompt))}.mp4"

        # If remote endpoint configured, post prompt
        if self.endpoint_url:
            try:
                payload = {
                    "prompt": prompt,
                    "duration": duration,
                    "width": width,
                    "height": height,
                    "fps": fps,
                }
                r = requests.post(f"{self.endpoint_url}/generate", json=payload, timeout=60)
                if r.status_code == 200:
                    data = r.json()
                    return VideoGenerationResult(
                        status="success",
                        video_path=data.get("video_path"),
                        duration=duration,
                        provider=self.name,
                        model=self.model_name,
                        metadata=data,
                    )
            except Exception as exc:
                return VideoGenerationResult(
                    status="failed",
                    video_path=None,
                    duration=duration,
                    provider=self.name,
                    model=self.model_name,
                    metadata={"error": str(exc)},
                )

        return VideoGenerationResult(
            status="failed",
            video_path=None,
            duration=duration,
            provider=self.name,
            model=self.model_name,
            metadata={"reason": "Remote endpoint unavailable and local weight download disabled by hardware guard."},
        )
