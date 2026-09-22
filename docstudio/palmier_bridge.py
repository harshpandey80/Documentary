"""
Palmier Pro Timeline Editor & MCP Bridge Module.
Evaluates OS compatibility, connects to local Palmier Pro MCP server,
provides generative B-roll fallback (Seedance, Kling, Nano Banana Pro),
and manages timeline synchronization without compromising headless automation.
"""

import os
import sys
import platform
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("docstudio.palmier")

DEFAULT_PALMIER_MCP_ENDPOINT = "http://127.0.0.1:19789/mcp"

class PalmierBridge:
    """
    Bridge interface for Palmier Pro timeline editor and its MCP server.
    Ensures safe, optional, and resilient communication with zero headless pipeline breakage.
    """

    def __init__(self, endpoint: str = DEFAULT_PALMIER_MCP_ENDPOINT):
        self.endpoint = os.environ.get("PALMIER_MCP_ENDPOINT", endpoint)
        self.compat_info = self.check_system_compatibility()

    @staticmethod
    def check_system_compatibility() -> Dict[str, Any]:
        """
        Verifies system against Palmier Pro minimum hardware & OS requirements:
        - OS: macOS 26 (Tahoe)
        - Hardware: Apple Silicon (arm64/aarch64)
        """
        sys_name = platform.system()
        machine = platform.machine().lower()
        release = platform.release()

        is_macos = sys_name == "Darwin"
        is_apple_silicon = is_macos and ("arm" in machine or "aarch64" in machine)
        
        # Check for macOS 26+ if running Darwin
        is_tahoe_or_newer = False
        if is_macos:
            try:
                major_version = int(release.split(".")[0])
                # macOS 26 corresponds to Darwin kernel 25+ or system version 26
                is_tahoe_or_newer = major_version >= 25 or platform.mac_ver()[0].startswith("26")
            except Exception:
                pass

        is_compatible = is_macos and is_apple_silicon and is_tahoe_or_newer

        if is_compatible:
            reason = "System meets Palmier Pro requirements: macOS 26 (Tahoe) on Apple Silicon."
        else:
            reason = (
                f"Palmier Pro requires macOS 26 (Tahoe) on Apple Silicon. "
                f"Current host: {sys_name} {release} ({platform.machine()}). "
                f"Native Palmier Pro execution is unsupported; headless FFmpeg engine remains primary."
            )

        return {
            "os_name": sys_name,
            "os_release": release,
            "machine": machine,
            "is_macos": is_macos,
            "is_apple_silicon": is_apple_silicon,
            "is_tahoe_or_newer": is_tahoe_or_newer,
            "is_compatible": is_compatible,
            "reason": reason,
        }

    def is_mcp_available(self, timeout: float = 1.0) -> bool:
        """
        Pings local Palmier Pro MCP endpoint to verify if the desktop app is active.
        Fails fast with zero delay to avoid blocking headless automation.
        """
        try:
            resp = requests.get(f"{self.endpoint}/health", timeout=timeout)
            return resp.status_code == 200
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive status of Palmier Pro compatibility and MCP connectivity."""
        mcp_active = self.is_mcp_available() if self.compat_info["is_compatible"] else False
        return {
            "system_compatibility": self.compat_info,
            "mcp_endpoint": self.endpoint,
            "mcp_active": mcp_active,
            "role": "Secondary / Manual Review & FCPXML Bridge" if not self.compat_info["is_compatible"] else "Optional Interactive MCP Timeline",
            "primary_engine": "FFmpeg Filtergraph Engine (100% Autonomous)",
        }

    def generate_broll_fallback(
        self,
        scene_id: str,
        prompt: str,
        dest_path: Path,
        model: str = "kling",
    ) -> Optional[Path]:
        """
        Tier 4 B-Roll Fallback: Requests generative footage/image from Palmier Pro's
        built-in generative models (Seedance, Kling, Nano Banana Pro) via MCP.
        
        CRITICAL: Assets generated must still pass through:
        1. License verification (commercial safety confirmation)
        2. Visual cohesion filter (LUT + 35mm grain + vignette)
        """
        if not self.compat_info["is_compatible"]:
            logger.debug("Palmier Pro generative fallback skipped: OS incompatible.")
            return None

        if not self.is_mcp_available():
            logger.debug("Palmier Pro generative fallback skipped: MCP server unreachable.")
            return None

        try:
            payload = {
                "action": "generate_broll",
                "model": model,  # "seedance", "kling", or "nano_banana_pro"
                "prompt": prompt,
                "scene_id": scene_id,
            }
            resp = requests.post(f"{self.endpoint}/tools/generate", json=payload, timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()
                asset_url = data.get("asset_url")
                if asset_url:
                    content = requests.get(asset_url, timeout=15.0).content
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    dest_path.write_bytes(content)
                    return dest_path
        except Exception as e:
            logger.warning(f"Palmier Pro generative call failed: {e}")

        return None

    def sync_timeline_to_mcp(self, timeline_data: Dict[str, Any]) -> bool:
        """
        Pushes the programmatic timeline (clips, cuts, tracks) directly to Palmier Pro's
        live UI timeline via MCP tools.
        """
        if not self.compat_info["is_compatible"] or not self.is_mcp_available():
            return False

        try:
            payload = {
                "action": "sync_timeline",
                "tracks": timeline_data.get("tracks", {}),
                "resolution": timeline_data.get("resolution", {}),
            }
            resp = requests.post(f"{self.endpoint}/tools/sync_timeline", json=payload, timeout=5.0)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to sync timeline to Palmier Pro MCP: {e}")
            return False
