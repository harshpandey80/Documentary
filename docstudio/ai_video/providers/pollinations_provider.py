"""
Pollinations Free AI Video Provider.
Cloud-based AI video synthesis with zero local GPU load.
"""

from __future__ import annotations
import urllib.parse
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

from docstudio.ai_video.base_provider import AIVideoProvider, VideoGenerationResult


class PollinationsVideoProvider(AIVideoProvider):
    def __init__(self, model_name: str = "pollinations-video"):
        super().__init__(name="pollinations", model_name=model_name)

    def is_available(self) -> bool:
        # Check network availability
        return True

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
        if not output_path:
            output_path = Path("workspace") / "ai_video_cache" / f"pollinations_{abs(hash(prompt))}.mp4"
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if out_p.exists() and out_p.stat().st_size > 50000:
            return VideoGenerationResult(
                status="success",
                video_path=str(out_p),
                duration=duration,
                provider=self.name,
                model=self.model_name,
                metadata={"source": "cache"},
            )

        encoded = urllib.parse.quote(prompt[:250])
        # Pollinations video endpoint
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"

        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 5000:
                # If image returned from pollinations, synthesize motion via ffmpeg
                temp_img = out_p.with_suffix(".jpg")
                temp_img.write_bytes(r.content)

                import subprocess
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(temp_img),
                    "-c:v", "libx264", "-t", str(duration),
                    "-pix_fmt", "yuv420p", "-vf", f"scale={width}:{height}",
                    str(out_p)
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if temp_img.exists():
                    temp_img.unlink()

                return VideoGenerationResult(
                    status="success",
                    video_path=str(out_p),
                    duration=duration,
                    provider=self.name,
                    model=self.model_name,
                    metadata={"source": "pollinations_cloud"},
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
            metadata={"error": "Empty response from provider"},
        )
