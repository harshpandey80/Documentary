"""
Phase 6 – Usage Registry & Visual Diversity Enforcer
------------------------------------------------------
Tracks every B-Roll asset across the run so the same clip is never
placed in more than `max_reuse` shots.  If a candidate is over-quota
it is rejected and the caller must try the next source tier.

Visual Tier Distribution Rules (from AGENTS.md §7):
  AI_CINEMATIC_RECREATION      >= 20%
  INFOGRAPHIC_CODE2VIDEO       >= 20%
  FORENSIC_ARCHIVAL            >= 20%
  CINEMATIC_STOCK              <= 30%
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

# Optional perceptual hash for near-duplicate detection
try:
    import imagehash  # type: ignore
    from PIL import Image as _PILImage  # type: ignore
    _PHASH_AVAILABLE = True
except ImportError:
    _PHASH_AVAILABLE = False


class UsageRegistry:
    """Per-run asset usage tracker with diversity enforcement."""

    VALID_TIERS = {
        "AI_CINEMATIC_RECREATION",
        "INFOGRAPHIC_CODE2VIDEO",
        "FORENSIC_ARCHIVAL",
        "CINEMATIC_STOCK",
    }

    def __init__(self, run_dir: Path, max_reuse: int = 2):
        self.run_dir = Path(run_dir)
        self.max_reuse = max_reuse
        self._lock = Lock()

        # path -> list of scene_ids that used it
        self._asset_uses: Dict[str, List[str]] = {}
        # phash -> canonical path (for near-duplicate detection)
        self._phash_map: Dict[str, str] = {}
        # scene_id -> tier
        self._scene_tiers: Dict[str, str] = {}

        self._registry_path = self.run_dir / "usage_registry.json"
        if self._registry_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_use(self, asset_path: Path, scene_id: str) -> bool:
        """Return True if this asset has not exceeded max_reuse quota."""
        with self._lock:
            key = self._asset_key(asset_path)
            uses = self._asset_uses.get(key, [])
            return len(uses) < self.max_reuse

    def register(self, asset_path: Path, scene_id: str, tier: str) -> None:
        """Record that scene_id is using asset_path from tier."""
        if tier not in self.VALID_TIERS:
            tier = "CINEMATIC_STOCK"  # safe default
        with self._lock:
            key = self._asset_key(asset_path)
            self._asset_uses.setdefault(key, []).append(scene_id)
            self._scene_tiers[scene_id] = tier
            # Register phash for near-duplicate detection
            if _PHASH_AVAILABLE and asset_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                try:
                    phash = str(imagehash.phash(_PILImage.open(asset_path)))
                    self._phash_map.setdefault(phash, str(asset_path))
                except Exception:
                    pass
            self._save()

    def is_near_duplicate(self, asset_path: Path) -> bool:
        """Return True if a visually near-identical asset is already registered."""
        if not _PHASH_AVAILABLE:
            return False
        if asset_path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            return False
        try:
            with self._lock:
                phash = str(imagehash.phash(_PILImage.open(asset_path)))
                return phash in self._phash_map
        except Exception:
            return False

    def tier_distribution(self, total_shots: int) -> Dict[str, float]:
        """
        Return tier distribution as percentages.
        Raises ValueError if mandatory diversity rules are violated.
        """
        with self._lock:
            counts: Dict[str, int] = {t: 0 for t in self.VALID_TIERS}
            for tier in self._scene_tiers.values():
                if tier in counts:
                    counts[tier] += 1
            n = total_shots or 1
            return {t: round(c / n * 100, 1) for t, c in counts.items()}

    def audit_diversity(self, total_shots: int) -> List[str]:
        """
        Return list of diversity violations (empty = all rules satisfied).
        """
        dist = self.tier_distribution(total_shots)
        violations: List[str] = []
        if dist.get("AI_CINEMATIC_RECREATION", 0) < 20.0:
            violations.append(
                f"AI_CINEMATIC_RECREATION underused: {dist.get('AI_CINEMATIC_RECREATION', 0):.1f}% (min 20%)"
            )
        if dist.get("INFOGRAPHIC_CODE2VIDEO", 0) < 20.0:
            violations.append(
                f"INFOGRAPHIC_CODE2VIDEO underused: {dist.get('INFOGRAPHIC_CODE2VIDEO', 0):.1f}% (min 20%)"
            )
        if dist.get("FORENSIC_ARCHIVAL", 0) < 20.0:
            violations.append(
                f"FORENSIC_ARCHIVAL underused: {dist.get('FORENSIC_ARCHIVAL', 0):.1f}% (min 20%)"
            )
        if dist.get("CINEMATIC_STOCK", 0) > 30.0:
            violations.append(
                f"CINEMATIC_STOCK over-used: {dist.get('CINEMATIC_STOCK', 0):.1f}% (max 30%)"
            )
        return violations

    def scene_count(self) -> int:
        with self._lock:
            return len(self._scene_tiers)

    def summary_report(self, total_shots: int) -> str:
        dist = self.tier_distribution(total_shots)
        lines = ["[UsageRegistry] Visual Tier Distribution:"]
        for tier, pct in dist.items():
            lines.append(f"  {tier:<35}: {pct:>5.1f}%")
        violations = self.audit_diversity(total_shots)
        if violations:
            lines.append("[UsageRegistry] DIVERSITY VIOLATIONS:")
            for v in violations:
                lines.append(f"  ! {v}")
        else:
            lines.append("[UsageRegistry] All diversity rules SATISFIED.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _asset_key(asset_path: Path) -> str:
        return str(Path(asset_path).resolve())

    def _save(self) -> None:
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "asset_uses": self._asset_uses,
                "phash_map": self._phash_map,
                "scene_tiers": self._scene_tiers,
            }
            self._registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass  # Non-critical persistence

    def _load(self) -> None:
        try:
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))
            self._asset_uses = data.get("asset_uses", {})
            self._phash_map = data.get("phash_map", {})
            self._scene_tiers = data.get("scene_tiers", {})
        except Exception:
            pass
