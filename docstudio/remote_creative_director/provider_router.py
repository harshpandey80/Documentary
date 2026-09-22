"""
DocStudio Remote Creative Director — Execution Provider Router.
Step 5, 6, 12, 13: Delegates shot execution to the centralized ProviderResolver,
integrates deterministic asset caching, and manages semantic fallbacks.
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from docstudio.remote_creative_director.manifest_schema import ShotDirective
from docstudio.remote_creative_director.provider_registry import (
    ProviderResolver,
    ExecutionProvider,
)
from docstudio.remote_creative_director.cache import AssetCacheManager
from docstudio.remote_creative_director.browser_bridge import audit_asset

logger = logging.getLogger("docstudio.execution_router")


class ExecutionRouter:
    """
    Directs shot execution using the central ProviderResolver and AssetCacheManager.
    """

    def __init__(self, cache_dir: Path, run_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.run_dir = Path(run_dir) if run_dir else self.cache_dir

        self.resolver = ProviderResolver(cache_dir=self.cache_dir, run_dir=self.run_dir)
        self.cache_mgr = AssetCacheManager(cache_dir=self.cache_dir / "asset_cache")
        self.stats: Dict[str, int] = {
            "total_requested": 0,
            "cache_hits": 0,
            "primary_successes": 0,
            "fallback_successes": 0,
            "total_failures": 0,
        }

    def execute_shot(
        self,
        shot: ShotDirective,
        topic: str,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        scene_narration: str = "",
    ) -> Optional[Path]:
        """
        Executes a single shot directive:
        1. Checks asset cache for identical request fingerprint.
        2. Dispatches to primary execution provider.
        3. Cascades gracefully through semantic fallbacks if necessary.
        4. Caches and returns valid output asset.
        """
        self.stats["total_requested"] += 1
        dest_video = self.cache_dir / f"{shot.shot_id}.mp4"

        # 1. Deterministic Caching Check
        fingerprint = self.cache_mgr.compute_fingerprint(
            topic=topic,
            shot=shot,
            width=width,
            height=height,
            fps=fps,
        )
        cached = self.cache_mgr.get_cached_asset(fingerprint)
        if cached and cached.exists() and cached.stat().st_size > 10000:
            logger.info(f"[Router] CACHE HIT for shot [{shot.shot_id}] ({fingerprint[:12]})")
            self.stats["cache_hits"] += 1
            if cached.resolve() != dest_video.resolve():
                import shutil
                shutil.copy2(str(cached), str(dest_video))
            return dest_video

        # 2. Check if direct output already exists from prior step
        if dest_video.exists() and dest_video.stat().st_size > 15000:
            self.cache_mgr.register_asset(
                fingerprint=fingerprint,
                asset_path=dest_video,
                shot_id=shot.shot_id,
                visual_type=str(shot.visual_type),
            )
            return dest_video

        # 3. Resolve Primary & Fallback Providers
        primary_provider, fallback_providers = self.resolver.resolve_providers(shot)

        # 4. Attempt Primary Execution
        logger.info(f"[Router] Executing shot [{shot.shot_id}] via primary provider: '{primary_provider.name}'")
        asset_path = primary_provider.execute(
            shot=shot,
            topic=topic,
            width=width,
            height=height,
            fps=fps,
            scene_narration=scene_narration,
            dest_path=dest_video,
        )

        if asset_path and Path(asset_path).exists() and Path(asset_path).stat().st_size > 5000:
            self.stats["primary_successes"] += 1
            self.cache_mgr.register_asset(
                fingerprint=fingerprint,
                asset_path=Path(asset_path),
                shot_id=shot.shot_id,
                visual_type=str(shot.visual_type),
            )
            return Path(asset_path)

        # 5. Cascading Semantic Fallback Execution
        logger.warning(f"[Router] Primary provider '{primary_provider.name}' failed for shot [{shot.shot_id}]. Triggering semantic fallback chain...")
        for fb_idx, fb_prov in enumerate(fallback_providers):
            logger.info(f"[Router] Trying fallback #{fb_idx + 1}: '{fb_prov.name}' for shot [{shot.shot_id}]")
            fb_asset = fb_prov.execute(
                shot=shot,
                topic=topic,
                width=width,
                height=height,
                fps=fps,
                scene_narration=scene_narration,
                dest_path=dest_video,
            )
            if fb_asset and Path(fb_asset).exists() and Path(fb_asset).stat().st_size > 5000:
                logger.info(f"[Router] Fallback provider '{fb_prov.name}' SUCCEEDED for shot [{shot.shot_id}]")
                self.stats["fallback_successes"] += 1
                self.cache_mgr.register_asset(
                    fingerprint=fingerprint,
                    asset_path=Path(fb_asset),
                    shot_id=shot.shot_id,
                    visual_type=str(shot.visual_type),
                )
                return Path(fb_asset)

        logger.error(f"[Router] All execution providers failed for shot [{shot.shot_id}].")
        self.stats["total_failures"] += 1
        return None

    def get_router_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            **self.cache_mgr.get_stats(),
        }
