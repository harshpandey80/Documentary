"""
DocStudio ComfyUI Video Provider.
Connects to local ComfyUI instance (http://127.0.0.1:8188) if active.
"""

from __future__ import annotations
import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

from docstudio.ai_video.base_provider import AIVideoProvider, VideoGenerationResult


class ComfyUIVideoProvider(AIVideoProvider):
    def __init__(self, comfy_url: Optional[str] = None, model_name: str = "comfyui-wan2.1"):
        super().__init__(name="comfyui", model_name=model_name)
        self.comfy_url = comfy_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.comfy_url}/system_stats", timeout=0.8)
            return r.status_code == 200
        except Exception:
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
                metadata={"reason": f"ComfyUI not reachable at {self.comfy_url}"},
            )

        # ComfyUI is live: could dispatch workflow
        return VideoGenerationResult(
            status="failed",
            video_path=None,
            duration=duration,
            provider=self.name,
            model=self.model_name,
            metadata={"reason": "No active workflow template configured."},
        )
