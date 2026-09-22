"""
DocStudio AI Video Base Provider & Hardware Detection.
Enforces standard provider interfaces and protects low-VRAM machines from huge diffusion downloads.
"""

from __future__ import annotations
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List


@dataclass
class VideoGenerationResult:
    status: str  # "success" | "fallback" | "failed"
    video_path: Optional[str] = None
    duration: float = 4.0
    provider: str = "unknown"
    model: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "video_path": self.video_path,
            "duration": self.duration,
            "provider": self.provider,
            "model": self.model,
            "metadata": dict(self.metadata),
        }


def get_hardware_profile() -> Dict[str, Any]:
    """
    Safely inspects local hardware without triggering heavy framework imports.
    Protects 16GB RAM / low-SSD environments (e.g. HP Aero 13) from out-of-memory crashes.
    """
    has_gpu = False
    vram_gb = 0.0
    device_name = "CPU"

    try:
        import torch
        if torch.cuda.is_available():
            has_gpu = True
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
            device_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    # Disk free space in GB
    free_disk_gb = 0.0
    try:
        total, used, free = shutil.disk_usage(Path.cwd())
        free_disk_gb = round(free / (1024**3), 2)
    except Exception:
        pass

    return {
        "has_gpu": has_gpu,
        "vram_gb": vram_gb,
        "device_name": device_name,
        "free_disk_gb": free_disk_gb,
        "can_run_local_diffusion": has_gpu and vram_gb >= 12.0,
    }


class AIVideoProvider(ABC):
    """
    Abstract AI Video Provider Interface.
    """

    def __init__(self, name: str, model_name: str = ""):
        self.name = name
        self.model_name = model_name

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is reachable or executable on this machine."""
        pass

    @abstractmethod
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
        """
        Executes video generation and returns a standard VideoGenerationResult.
        """
        pass
