"""
DocStudio AI Video Provider Architecture.
Pluggable provider interface supporting cloud APIs, ComfyUI, LTX-Video,
and lightweight CPU parallax camera synthesis with strict hardware protection.
"""

from docstudio.ai_video.base_provider import AIVideoProvider, VideoGenerationResult
from docstudio.ai_video.factory import get_video_provider, VideoProviderFactory

__all__ = [
    "AIVideoProvider",
    "VideoGenerationResult",
    "get_video_provider",
    "VideoProviderFactory",
]
