"""
DocStudio AI Video Provider Factory.
Orchestrates multi-provider selection, hardware adaptation, and seamless fallback.
"""

from __future__ import annotations
import os
from typing import Dict, Optional, List
from pathlib import Path

from docstudio.ai_video.base_provider import AIVideoProvider, VideoGenerationResult, get_hardware_profile
from docstudio.ai_video.providers.pollinations_provider import PollinationsVideoProvider
from docstudio.ai_video.providers.parallax_provider import ParallaxCameraProvider
from docstudio.ai_video.providers.ltx_provider import LTXVideoProvider
from docstudio.ai_video.providers.comfyui_provider import ComfyUIVideoProvider
from docstudio.ai_video.providers.meta_ai_provider import MetaAIVideoProvider


class VideoProviderFactory:
    """
    Factory for instantiating and falling back across AI video providers.
    """

    @staticmethod
    def get_provider(name: str = "auto") -> AIVideoProvider:
        name_lower = (name or "auto").lower().strip()

        if name_lower in ["meta_ai", "meta"]:
            return MetaAIVideoProvider()
        elif name_lower == "pollinations":
            return PollinationsVideoProvider()
        elif name_lower in ["parallax", "cpu", "kenburns"]:
            return ParallaxCameraProvider()
        elif name_lower == "ltx":
            return LTXVideoProvider()
        elif name_lower == "comfyui":
            return ComfyUIVideoProvider()

        # "auto" mode: select best available based on hardware & authenticated sessions
        # 1. Try Meta AI Image Synthesis + Pipeline Motion if authenticated profile exists
        meta_prov = MetaAIVideoProvider()
        if meta_prov.is_available():
            return meta_prov

        # 2. Try ComfyUI if locally running
        comfy = ComfyUIVideoProvider()
        if comfy.is_available():
            return comfy

        # 3. Try LTX if remote endpoint or high VRAM GPU is available
        ltx = LTXVideoProvider()
        if ltx.is_available():
            return ltx

        # 4. Try Pollinations cloud
        pollinations = PollinationsVideoProvider()
        if pollinations.is_available():
            return pollinations

        # 5. Guaranteed CPU fallback
        return ParallaxCameraProvider()

    @staticmethod
    def generate_with_fallback(
        prompt: str,
        duration: float = 4.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        preferred_provider: str = "auto",
        output_path: Optional[Path | str] = None,
    ) -> VideoGenerationResult:
        """
        Executes fallback chain:
        Preferred / AI Video -> Parallax Camera -> Still Frame.
        """
        provider_order: List[AIVideoProvider] = []
        if preferred_provider != "auto":
            provider_order.append(VideoProviderFactory.get_provider(preferred_provider))

        # Always include Meta AI, pollinations and parallax in order
        provider_order.extend([
            MetaAIVideoProvider(),
            PollinationsVideoProvider(),
            ParallaxCameraProvider(),
        ])

        last_result = None
        for prov in provider_order:
            if prov.is_available():
                res = prov.generate_video(
                    prompt=prompt,
                    duration=duration,
                    width=width,
                    height=height,
                    fps=fps,
                    output_path=output_path,
                )
                if res.status == "success" and res.video_path and Path(res.video_path).exists():
                    return res
                last_result = res

        # Fallback to parallax guaranteed
        parallax = ParallaxCameraProvider()
        return parallax.generate_video(
            prompt=prompt,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            output_path=output_path,
        )


def get_video_provider(name: str = "auto") -> AIVideoProvider:
    return VideoProviderFactory.get_provider(name)
