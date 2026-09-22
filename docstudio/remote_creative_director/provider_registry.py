"""
DocStudio Remote Creative Director — Centralized Execution Provider Registry.
Step 5 & 13: Maps visual types to authoritative execution providers with graceful fallback resolution.
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from docstudio.remote_creative_director.manifest_schema import (
    ShotDirective,
    SourceStrategy,
)
from docstudio.remote_creative_director.visual_registry import (
    VisualType,
    VisualTypeRegistry,
)

logger = logging.getLogger("docstudio.provider_registry")


class ExecutionProvider(ABC):
    """Abstract base contract for local and remote visual execution engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def can_execute(self, vtype: VisualType, strategy: SourceStrategy) -> bool:
        pass

    @abstractmethod
    def execute(
        self,
        shot: ShotDirective,
        topic: str,
        width: int,
        height: int,
        fps: int,
        scene_narration: str,
        dest_path: Path,
    ) -> Optional[Path]:
        pass


# ─── 1. MAP PROVIDER ──────────────────────────────────────────────────────────
class MapExecutionProvider(ExecutionProvider):
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    @property
    def name(self) -> str:
        return "map_animation"

    def can_execute(self, vtype: VisualType, strategy: SourceStrategy) -> bool:
        return vtype in (VisualType.MAP, VisualType.MAP_ANIMATION) or strategy == SourceStrategy.PROCEDURAL_MAP

    def execute(
        self,
        shot: ShotDirective,
        topic: str,
        width: int,
        height: int,
        fps: int,
        scene_narration: str,
        dest_path: Path,
    ) -> Optional[Path]:
        try:
            from docstudio.map_animation import MapAnimationEngine
            engine = MapAnimationEngine(cache_dir=self.cache_dir)
            origin = shot.execution_metadata.get("origin") or topic
            dest = shot.execution_metadata.get("destination") or "Atlantic"
            rendered = engine.render_travel_route(
                origin_name=origin,
                dest_name=dest,
                dest_video=dest_path,
                duration=shot.duration,
                width=width,
                height=height,
                fps=fps,
            )
            if rendered and Path(rendered).exists() and Path(rendered).stat().st_size > 5000:
                return Path(rendered)
        except Exception as exc:
            logger.warning(f"[{self.name}] Execution error: {exc}")
        return None


# ─── 2. CHART PROVIDER ────────────────────────────────────────────────────────
class ChartExecutionProvider(ExecutionProvider):
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    @property
    def name(self) -> str:
        return "number_graphics"

    def can_execute(self, vtype: VisualType, strategy: SourceStrategy) -> bool:
        return vtype in (VisualType.DATA_CHART, VisualType.INFOGRAPHIC) or strategy == SourceStrategy.PROCEDURAL_CHART

    def execute(
        self,
        shot: ShotDirective,
        topic: str,
        width: int,
        height: int,
        fps: int,
        scene_narration: str,
        dest_path: Path,
    ) -> Optional[Path]:
        try:
            from docstudio.number_graphics import NumberGraphicsEngine
            engine = NumberGraphicsEngine(cache_dir=self.cache_dir)
            title = shot.visual_reason or topic
            data = shot.execution_metadata.get("data", [10, 25, 55, 90])
            labels = shot.execution_metadata.get("labels", ["Phase 1", "Phase 2", "Phase 3", "Phase 4"])
            rendered = engine.render_chart(
                title=title,
                data=data,
                labels=labels,
                dest_video=dest_path,
                duration=shot.duration,
                width=width,
                height=height,
                fps=fps,
            )
            if rendered and Path(rendered).exists() and Path(rendered).stat().st_size > 5000:
                return Path(rendered)
        except Exception as exc:
            logger.warning(f"[{self.name}] Execution error: {exc}")
        return None


# ─── 3. EVIDENCE / DOSSIER PROVIDER ──────────────────────────────────────────
class EvidenceExecutionProvider(ExecutionProvider):
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    @property
    def name(self) -> str:
        return "vox_motion_graphics"

    def can_execute(self, vtype: VisualType, strategy: SourceStrategy) -> bool:
        return vtype in (
            VisualType.AUTHENTIC_EVIDENCE,
            VisualType.DOCUMENT,
            VisualType.REAL_ARCHIVAL,
            VisualType.PHOTOGRAPH,
            VisualType.TIMELINE_DIAGRAM,
            VisualType.SCREEN_RECREATION,
            VisualType.MOTION_GRAPHIC,
        ) or strategy == SourceStrategy.PROCEDURAL_DOCUMENT

    def execute(
        self,
        shot: ShotDirective,
        topic: str,
        width: int,
        height: int,
        fps: int,
        scene_narration: str,
        dest_path: Path,
    ) -> Optional[Path]:
        try:
            from docstudio.vox_motion_graphics import VoxMotionGraphicsEngine
            engine = VoxMotionGraphicsEngine(cache_dir=self.cache_dir)
            rendered = engine.render_declassified_dossier(
                topic=topic,
                document_body=scene_narration or shot.visual_reason,
                dest_video=dest_path,
                duration=shot.duration,
                width=width,
                height=height,
                fps=fps,
                scene_id=shot.shot_id,
            )
            if rendered and Path(rendered).exists() and Path(rendered).stat().st_size > 5000:
                return Path(rendered)
        except Exception as exc:
            logger.warning(f"[{self.name}] Execution error: {exc}")
        return None


# ─── 4. BROWSER VISUAL PROVIDER (Web Flow / Cloud) ───────────────────────────
class BrowserVisualExecutionProvider(ExecutionProvider):
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    @property
    def name(self) -> str:
        return "browser_flow"

    def can_execute(self, vtype: VisualType, strategy: SourceStrategy) -> bool:
        return vtype in (
            VisualType.AI_VIDEO,
            VisualType.AI_IMAGE_TO_VIDEO,
            VisualType.AI_IMAGE,
            VisualType.BROWSER_GENERATED_VISUAL,
            VisualType.CINEMATIC_RECONSTRUCTION,
        ) or strategy in (SourceStrategy.GENERATE_AI_VIDEO, SourceStrategy.GENERATE_AI_IMAGE)

    def execute(
        self,
        shot: ShotDirective,
        topic: str,
        width: int,
        height: int,
        fps: int,
        scene_narration: str,
        dest_path: Path,
    ) -> Optional[Path]:
        try:
            from docstudio.visual_providers.browser import get_browser_provider
            browser_prov = get_browser_provider()
            res = browser_prov.generate_video_from_shot(
                shot=shot,
                topic=topic,
                width=width,
                height=height,
                fps=fps,
                dest_video=dest_path,
            )
            if res and Path(res).exists() and Path(res).stat().st_size > 10000:
                return Path(res)
        except Exception as exc:
            logger.warning(f"[{self.name}] Execution error: {exc}")
        return None


# ─── 5. PROCEDURAL MOTION (Parallax / Ken Burns CPU Guaranteed) ──────────────
class ProceduralMotionExecutionProvider(ExecutionProvider):
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    @property
    def name(self) -> str:
        return "procedural_motion"

    def can_execute(self, vtype: VisualType, strategy: SourceStrategy) -> bool:
        return True  # Universal fallback for any visual requiring cinematic movement

    def execute(
        self,
        shot: ShotDirective,
        topic: str,
        width: int,
        height: int,
        fps: int,
        scene_narration: str,
        dest_path: Path,
    ) -> Optional[Path]:
        try:
            from docstudio.ai_video.factory import VideoProviderFactory
            res = VideoProviderFactory.generate_with_fallback(
                prompt=shot.prompt or shot.visual_reason or topic,
                duration=shot.duration,
                width=width,
                height=height,
                fps=fps,
                output_path=dest_path,
            )
            if res.video_path and Path(res.video_path).exists() and Path(res.video_path).stat().st_size > 5000:
                return Path(res.video_path)
        except Exception as exc:
            logger.warning(f"[{self.name}] Execution error: {exc}")
        return None


# ─── 6. STOCK B-ROLL PROVIDER ────────────────────────────────────────────────
class StockExecutionProvider(ExecutionProvider):
    def __init__(self, cache_dir: Path, run_dir: Optional[Path] = None):
        self.cache_dir = cache_dir
        self.run_dir = run_dir or cache_dir

    @property
    def name(self) -> str:
        return "broll_matcher"

    def can_execute(self, vtype: VisualType, strategy: SourceStrategy) -> bool:
        return vtype in (
            VisualType.STOCK_BROLL,
            VisualType.STOCK_FOOTAGE,
            VisualType.CINEMATIC_BROLL,
            VisualType.ATMOSPHERIC_VISUAL,
            VisualType.TRANSITION,
        ) or strategy == SourceStrategy.RETRIEVE_ARCHIVE_STOCK

    def execute(
        self,
        shot: ShotDirective,
        topic: str,
        width: int,
        height: int,
        fps: int,
        scene_narration: str,
        dest_path: Path,
    ) -> Optional[Path]:
        try:
            from docstudio.broll_matcher import BRollMatcher
            matcher = BRollMatcher(cache_dir=self.cache_dir)
            asset = matcher.acquire_visual_for_scene(
                scene_id=shot.shot_id,
                keywords=[topic, shot.purpose.value if hasattr(shot.purpose, "value") else str(shot.purpose)],
                visual_prompt=shot.prompt or shot.visual_reason,
                topic=topic,
                width=width,
                height=height,
                duration=shot.duration,
                narration=scene_narration,
                run_dir=self.run_dir,
            )
            if asset and Path(asset).exists() and Path(asset).stat().st_size > 5000:
                return Path(asset)
        except Exception as exc:
            logger.warning(f"[{self.name}] Execution error: {exc}")
        return None


# ─── CENTRAL PROVIDER RESOLVER ───────────────────────────────────────────────
class ProviderResolver:
    """
    Central authoritative resolver that resolves any shot directive to its primary
    execution provider and an ordered chain of semantically appropriate fallbacks.
    """

    def __init__(self, cache_dir: Path, run_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir)
        self.run_dir = Path(run_dir) if run_dir else self.cache_dir

        self.providers: Dict[str, ExecutionProvider] = {
            "map_animation": MapExecutionProvider(self.cache_dir),
            "number_graphics": ChartExecutionProvider(self.cache_dir),
            "vox_motion_graphics": EvidenceExecutionProvider(self.cache_dir),
            "browser_flow": BrowserVisualExecutionProvider(self.cache_dir),
            "procedural_motion": ProceduralMotionExecutionProvider(self.cache_dir),
            "broll_matcher": StockExecutionProvider(self.cache_dir, self.run_dir),
        }

    def get_provider(self, name: str) -> Optional[ExecutionProvider]:
        return self.providers.get(name)

    def resolve_providers(self, shot: ShotDirective) -> Tuple[ExecutionProvider, List[ExecutionProvider]]:
        """
        Returns (primary_provider, [fallback_providers]).
        Uses the visual type registry's semantic fallback chain to guarantee semantic alignment.
        """
        vtype = shot.visual_type
        strategy = shot.source_strategy
        default_prov_name = VisualTypeRegistry.get_default_provider(vtype)

        primary = self.providers.get(default_prov_name) or self.providers["broll_matcher"]

        # Build fallback chain based on semantic visual fallbacks
        fallbacks: List[ExecutionProvider] = []
        fb_types = VisualTypeRegistry.resolve_fallback_chain(vtype)
        for fb_t in fb_types:
            fb_prov_name = VisualTypeRegistry.get_default_provider(fb_t)
            prov = self.providers.get(fb_prov_name)
            if prov and prov != primary and prov not in fallbacks:
                fallbacks.append(prov)

        # Ensure universal procedural motion and stock are always in fallback sequence
        if self.providers["procedural_motion"] not in fallbacks and self.providers["procedural_motion"] != primary:
            fallbacks.append(self.providers["procedural_motion"])
        if self.providers["broll_matcher"] not in fallbacks and self.providers["broll_matcher"] != primary:
            fallbacks.append(self.providers["broll_matcher"])

        return primary, fallbacks
