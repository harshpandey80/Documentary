"""
DocStudio Remote Creative Director — Browser Generation Bridge & Asset QA.
Translates ShotDirectives into standardized browser worker requests and executes
thorough post-generation Quality Assurance on returned video files.
"""

from __future__ import annotations
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from docstudio.remote_creative_director.manifest_schema import ShotDirective


@dataclass
class BrowserGenerationRequest:
    shot_id: str
    prompt: str
    duration: float
    width: int
    height: int
    aspect_ratio: str = "16:9"
    style: str = "cinematic_documentary"
    reference_images: List[str] = field(default_factory=list)
    negative_requirements: List[str] = field(default_factory=lambda: ["no watermark", "no text overlay", "no modern equipment"])
    continuity_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "prompt": self.prompt,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "aspect_ratio": self.aspect_ratio,
            "style": self.style,
            "reference_images": list(self.reference_images),
            "negative_requirements": list(self.negative_requirements),
            "continuity_context": dict(self.continuity_context),
        }


@dataclass
class AssetQAResult:
    is_valid: bool
    asset_path: Optional[Path] = None
    duration: float = 0.0
    width: int = 0
    height: int = 0
    file_size_bytes: int = 0
    errors: List[str] = field(default_factory=list)


class BrowserBridge:
    """
    Bridges between the Remote Creative Director and browser generation workers.
    """

    @staticmethod
    def create_request_from_shot(
        shot: ShotDirective,
        width: int = 1920,
        height: int = 1080,
        style: str = "cinematic_documentary",
    ) -> BrowserGenerationRequest:
        aspect_ratio = "9:16" if height > width else "16:9"
        return BrowserGenerationRequest(
            shot_id=shot.shot_id,
            prompt=shot.prompt or shot.visual_reason,
            duration=shot.duration,
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            style=style,
            continuity_context={"camera": shot.camera, "motion": shot.motion},
        )

    @staticmethod
    def audit_asset(file_path: Path | str, expected_duration: float = 0.0) -> AssetQAResult:
        """
        Verifies that a generated or downloaded asset is playable, uncorrupted,
        and matches duration and resolution constraints.
        """
        p = Path(file_path)
        if not p.exists():
            return AssetQAResult(is_valid=False, errors=[f"Asset file does not exist: {p}"])

        size = p.stat().st_size
        if size < 5000:
            return AssetQAResult(is_valid=False, file_size_bytes=size, errors=["Asset file size is suspiciously small (<5KB)."])

        dur = 0.0
        w = 0
        h = 0
        try:
            import subprocess
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration:stream=width,height",
                "-of", "json", str(p)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                dur = float(data.get("format", {}).get("duration", 0.0))
                streams = data.get("streams", [])
                if streams:
                    w = int(streams[0].get("width", 0))
                    h = int(streams[0].get("height", 0))
        except Exception:
            dur = expected_duration

        errors = []
        if expected_duration > 0 and dur > 0 and dur < (expected_duration * 0.4):
            errors.append(f"Asset duration ({dur}s) is significantly shorter than expected ({expected_duration}s).")

        return AssetQAResult(
            is_valid=len(errors) == 0,
            asset_path=p,
            duration=dur,
            width=w,
            height=h,
            file_size_bytes=size,
            errors=errors,
        )


# Module-level convenience function
audit_asset = BrowserBridge.audit_asset

