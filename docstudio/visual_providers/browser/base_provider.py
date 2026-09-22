"""
DocStudio Browser Visual Provider — Abstract Base Provider.
Defines the standard interface for browser-based remote creative generation.
The browser worker acts strictly as 'Hands' (Execution), NOT the 'Brain' (Director).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from docstudio.remote_creative_director.manifest_schema import ShotDirective
from docstudio.remote_creative_director.browser_bridge import BrowserGenerationRequest


@dataclass
class BrowserGenerationResponse:
    status: str  # "success" | "pending" | "failed"
    asset_path: Optional[str] = None
    task_id: str = ""
    provider_name: str = "browser_flow"
    metadata: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "asset_path": self.asset_path,
            "task_id": self.task_id,
            "provider_name": self.provider_name,
            "metadata": dict(self.metadata or {}),
        }


class BrowserVisualProvider(ABC):
    """
    Abstract interface for browser automation workers.
    """

    def __init__(self, name: str = "browser_flow"):
        self.name = name

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the browser worker environment is configured and reachable."""
        pass

    @abstractmethod
    def generate_image(self, request: BrowserGenerationRequest) -> BrowserGenerationResponse:
        """Generates an image via browser automation."""
        pass

    @abstractmethod
    def generate_video(self, request: BrowserGenerationRequest) -> BrowserGenerationResponse:
        """Generates a video clip via browser automation."""
        pass

    @abstractmethod
    def download_asset(self, remote_url: str, dest_path: Path) -> Optional[Path]:
        """Downloads a generated asset to local storage."""
        pass

    @abstractmethod
    def generate_video_from_shot(
        self,
        shot: ShotDirective,
        topic: str,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        dest_video: Optional[Path] = None,
    ) -> Optional[Path]:
        """Convenience method to execute a shot directive into an MP4 file."""
        pass
