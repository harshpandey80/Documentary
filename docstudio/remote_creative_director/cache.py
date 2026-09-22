"""
DocStudio Remote Creative Director — Deterministic Asset Cache Manager.
Step 11 & 12: Generates cryptographic request fingerprints and manages reusable media assets.
Prevents duplicate generations, saves remote browser/API credits, and accelerates production.
"""

from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from docstudio.remote_creative_director.manifest_schema import ShotDirective


class AssetCacheManager:
    """
    Manages deterministic asset caching and fingerprinting across documentary runs.
    """

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "asset_cache_index.json"
        self._index: Dict[str, Dict[str, Any]] = self._load_index()
        self.hits = 0
        self.misses = 0

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self) -> None:
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def compute_fingerprint(
        topic: str,
        shot: ShotDirective,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
    ) -> str:
        """Computes a deterministic SHA-256 fingerprint for a visual generation request."""
        vtype_val = shot.visual_type.value if hasattr(shot.visual_type, "value") else str(shot.visual_type)
        strat_val = shot.source_strategy.value if hasattr(shot.source_strategy, "value") else str(shot.source_strategy)
        
        fingerprint_payload = {
            "topic": topic.strip().lower(),
            "purpose": str(shot.purpose),
            "visual_type": vtype_val,
            "source_strategy": strat_val,
            "prompt": (shot.prompt or shot.visual_reason).strip().lower(),
            "duration": round(shot.duration, 1),
            "resolution": f"{width}x{height}@{fps}",
            "execution_metadata": shot.execution_metadata,
        }
        raw_bytes = json.dumps(fingerprint_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()

    def get_cached_asset(self, fingerprint: str) -> Optional[Path]:
        """Checks if an asset matching the fingerprint exists and is valid."""
        if fingerprint in self._index:
            entry = self._index[fingerprint]
            asset_path = Path(entry.get("path", ""))
            if asset_path.exists() and asset_path.stat().st_size > 15000:
                self.hits += 1
                return asset_path
            else:
                # Evict corrupted or missing entry
                del self._index[fingerprint]
                self._save_index()
        self.misses += 1
        return None

    def register_asset(
        self,
        fingerprint: str,
        asset_path: Path,
        shot_id: str,
        visual_type: str,
    ) -> Path:
        """Caches an asset and records it in the index."""
        asset_path = Path(asset_path)
        if not asset_path.exists():
            return asset_path

        cached_dest = self.cache_dir / f"cached_{fingerprint[:16]}{asset_path.suffix}"
        if asset_path.resolve() != cached_dest.resolve():
            shutil.copy2(str(asset_path), str(cached_dest))

        self._index[fingerprint] = {
            "path": str(cached_dest),
            "shot_id": shot_id,
            "visual_type": visual_type,
            "size_bytes": cached_dest.stat().st_size,
        }
        self._save_index()
        return cached_dest

    def get_stats(self) -> Dict[str, int]:
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "total_cached_entries": len(self._index),
        }
