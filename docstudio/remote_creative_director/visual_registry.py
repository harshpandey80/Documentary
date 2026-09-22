"""
DocStudio Remote Creative Director — Visual Type Registry & Semantic Fallbacks.
Step 4, 5, 6: Centralizes all documentary visual media types, identifies execution support status
(SUPPORTED_NOW vs PLANNED), maps default execution providers, and enforces semantic fallback chains.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple


class TruthCategory(str, Enum):
    """Explicit truth classification of documentary visual material."""
    DOCUMENTARY_EVIDENCE = "DOCUMENTARY_EVIDENCE"
    ARCHIVAL = "ARCHIVAL"
    CONTEMPORARY = "CONTEMPORARY"
    RECONSTRUCTION = "RECONSTRUCTION"
    AI_GENERATED = "AI_GENERATED"
    CONCEPTUAL = "CONCEPTUAL"
    ILLUSTRATIVE = "ILLUSTRATIVE"


class CostClass(str, Enum):
    """Cost profile for generating/acquiring the visual."""
    FREE_PROCEDURAL = "low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComputeClass(str, Enum):
    """Where visual execution occurs."""
    LOCAL = "local"
    BROWSER = "browser"
    REMOTE = "remote"


class VisualType(str, Enum):
    # Tier 1: Evidence & Primary Archives
    AUTHENTIC_EVIDENCE = "AUTHENTIC_EVIDENCE"
    REAL_ARCHIVAL = "REAL_ARCHIVAL"
    DOCUMENT = "DOCUMENT"
    PHOTOGRAPH = "PHOTOGRAPH"
    ARCHIVAL_FOOTAGE = "ARCHIVAL_FOOTAGE"

    # Tier 2: Data, Geography & Sequences
    MAP = "MAP"
    MAP_ANIMATION = "MAP_ANIMATION"
    DATA_CHART = "DATA_CHART"
    TIMELINE_DIAGRAM = "TIMELINE_DIAGRAM"
    DIAGRAM = "DIAGRAM"
    INFOGRAPHIC = "INFOGRAPHIC"

    # Tier 3: Motion & Graphics
    MOTION_GRAPHIC = "MOTION_GRAPHIC"
    KINETIC_TYPOGRAPHY = "KINETIC_TYPOGRAPHY"
    SCREEN_RECREATION = "SCREEN_RECREATION"
    UI_SIMULATION = "UI_SIMULATION"

    # Tier 4: AI & Cinematic Reconstructions
    CINEMATIC_RECONSTRUCTION = "CINEMATIC_RECONSTRUCTION"
    AI_IMAGE_TO_VIDEO = "AI_IMAGE_TO_VIDEO"
    AI_IMAGE = "AI_IMAGE"
    AI_VIDEO = "AI_VIDEO"
    BROWSER_GENERATED_VISUAL = "BROWSER_GENERATED_VISUAL"

    # Tier 5: Stock & Atmosphere
    STOCK_BROLL = "STOCK_BROLL"
    STOCK_FOOTAGE = "STOCK_FOOTAGE"
    CINEMATIC_BROLL = "CINEMATIC_BROLL"
    ATMOSPHERIC_VISUAL = "ATMOSPHERIC_VISUAL"
    INTERVIEW = "INTERVIEW"
    RECONSTRUCTION = "RECONSTRUCTION"
    TRANSITION = "TRANSITION"


# ─── EXECUTION CAPABILITY PARTITION ──────────────────────────────────────────

SUPPORTED_NOW: Set[VisualType] = {
    VisualType.AUTHENTIC_EVIDENCE,
    VisualType.REAL_ARCHIVAL,
    VisualType.DOCUMENT,
    VisualType.PHOTOGRAPH,
    VisualType.MAP,
    VisualType.MAP_ANIMATION,
    VisualType.DATA_CHART,
    VisualType.TIMELINE_DIAGRAM,
    VisualType.INFOGRAPHIC,
    VisualType.MOTION_GRAPHIC,
    VisualType.SCREEN_RECREATION,
    VisualType.CINEMATIC_RECONSTRUCTION,
    VisualType.AI_IMAGE_TO_VIDEO,
    VisualType.AI_IMAGE,
    VisualType.AI_VIDEO,
    VisualType.BROWSER_GENERATED_VISUAL,
    VisualType.STOCK_BROLL,
    VisualType.STOCK_FOOTAGE,
    VisualType.CINEMATIC_BROLL,
    VisualType.ATMOSPHERIC_VISUAL,
    VisualType.TRANSITION,
}

PLANNED: Set[VisualType] = {
    VisualType.ARCHIVAL_FOOTAGE,
    VisualType.DIAGRAM,
    VisualType.KINETIC_TYPOGRAPHY,
    VisualType.UI_SIMULATION,
    VisualType.INTERVIEW,
    VisualType.RECONSTRUCTION,
}


# ─── DEFAULT PROVIDER MAPPING ────────────────────────────────────────────────

DEFAULT_PROVIDER_MAPPING: Dict[VisualType, str] = {
    # Maps
    VisualType.MAP: "map_animation",
    VisualType.MAP_ANIMATION: "map_animation",
    # Charts & Stats
    VisualType.DATA_CHART: "number_graphics",
    VisualType.INFOGRAPHIC: "number_graphics",
    # Evidence & Documents
    VisualType.AUTHENTIC_EVIDENCE: "vox_motion_graphics",
    VisualType.DOCUMENT: "vox_motion_graphics",
    VisualType.REAL_ARCHIVAL: "vox_motion_graphics",
    VisualType.PHOTOGRAPH: "vox_motion_graphics",
    VisualType.TIMELINE_DIAGRAM: "vox_motion_graphics",
    VisualType.SCREEN_RECREATION: "vox_motion_graphics",
    # AI Imagery & Video
    VisualType.AI_VIDEO: "browser_flow",
    VisualType.AI_IMAGE_TO_VIDEO: "browser_flow",
    VisualType.AI_IMAGE: "browser_flow",
    VisualType.BROWSER_GENERATED_VISUAL: "browser_flow",
    VisualType.CINEMATIC_RECONSTRUCTION: "browser_flow",
    # Stock & Atmosphere
    VisualType.STOCK_BROLL: "broll_matcher",
    VisualType.STOCK_FOOTAGE: "broll_matcher",
    VisualType.CINEMATIC_BROLL: "broll_matcher",
    VisualType.ATMOSPHERIC_VISUAL: "broll_matcher",
    VisualType.TRANSITION: "broll_matcher",
    # Motion Graphics
    VisualType.MOTION_GRAPHIC: "vox_motion_graphics",
}


# ─── SEMANTIC FALLBACK SYSTEM ────────────────────────────────────────────────
# Never blindly substitute random stock footage for a geographic explanation.
# Fallback choices MUST preserve semantic communicative purpose.

SEMANTIC_FALLBACKS: Dict[VisualType, List[VisualType]] = {
    # AI Video falls back to 2.5D Parallax, then High-Res Still, then Historical Stock, then Motion Graphic
    VisualType.AI_VIDEO: [
        VisualType.AI_IMAGE_TO_VIDEO,
        VisualType.AI_IMAGE,
        VisualType.CINEMATIC_BROLL,
        VisualType.MOTION_GRAPHIC,
    ],
    VisualType.AI_IMAGE_TO_VIDEO: [
        VisualType.AI_IMAGE,
        VisualType.CINEMATIC_BROLL,
        VisualType.MOTION_GRAPHIC,
    ],
    VisualType.AI_IMAGE: [
        VisualType.PHOTOGRAPH,
        VisualType.CINEMATIC_BROLL,
        VisualType.MOTION_GRAPHIC,
    ],
    # Geography falls back strictly to static map, timeline, or archival photograph
    VisualType.MAP: [
        VisualType.MAP_ANIMATION,
        VisualType.TIMELINE_DIAGRAM,
        VisualType.DOCUMENT,
        VisualType.CINEMATIC_BROLL,
    ],
    VisualType.MAP_ANIMATION: [
        VisualType.MAP,
        VisualType.TIMELINE_DIAGRAM,
        VisualType.CINEMATIC_BROLL,
    ],
    # Numerical data falls back strictly to infographic card, motion graphic, or document highlight
    VisualType.DATA_CHART: [
        VisualType.INFOGRAPHIC,
        VisualType.MOTION_GRAPHIC,
        VisualType.DOCUMENT,
    ],
    VisualType.INFOGRAPHIC: [
        VisualType.DATA_CHART,
        VisualType.MOTION_GRAPHIC,
        VisualType.DOCUMENT,
    ],
    VisualType.TIMELINE_DIAGRAM: [
        VisualType.DATA_CHART,
        VisualType.DOCUMENT,
        VisualType.MOTION_GRAPHIC,
    ],
    # Evidence falls back strictly to document, archival photo, or authenticated record
    VisualType.AUTHENTIC_EVIDENCE: [
        VisualType.DOCUMENT,
        VisualType.REAL_ARCHIVAL,
        VisualType.PHOTOGRAPH,
    ],
    VisualType.DOCUMENT: [
        VisualType.AUTHENTIC_EVIDENCE,
        VisualType.REAL_ARCHIVAL,
        VisualType.PHOTOGRAPH,
    ],
    VisualType.REAL_ARCHIVAL: [
        VisualType.PHOTOGRAPH,
        VisualType.AUTHENTIC_EVIDENCE,
        VisualType.CINEMATIC_BROLL,
    ],
    VisualType.PHOTOGRAPH: [
        VisualType.REAL_ARCHIVAL,
        VisualType.CINEMATIC_BROLL,
    ],
    VisualType.ARCHIVAL_FOOTAGE: [
        VisualType.REAL_ARCHIVAL,
        VisualType.PHOTOGRAPH,
        VisualType.CINEMATIC_BROLL,
    ],
    VisualType.SCREEN_RECREATION: [
        VisualType.MOTION_GRAPHIC,
        VisualType.CINEMATIC_BROLL,
    ],
    VisualType.CINEMATIC_RECONSTRUCTION: [
        VisualType.AI_IMAGE_TO_VIDEO,
        VisualType.AI_IMAGE,
        VisualType.CINEMATIC_BROLL,
    ],
    VisualType.CINEMATIC_BROLL: [
        VisualType.STOCK_BROLL,
        VisualType.ATMOSPHERIC_VISUAL,
    ],
    VisualType.STOCK_BROLL: [
        VisualType.ATMOSPHERIC_VISUAL,
        VisualType.MOTION_GRAPHIC,
    ],
    VisualType.ATMOSPHERIC_VISUAL: [
        VisualType.STOCK_BROLL,
        VisualType.MOTION_GRAPHIC,
    ],
    VisualType.TRANSITION: [
        VisualType.ATMOSPHERIC_VISUAL,
    ],
}


class VisualTypeRegistry:
    """Central registry providing visual type query, validation, and fallback resolution."""

    @classmethod
    def normalize_type(cls, raw_type: str | VisualType) -> Optional[VisualType]:
        """Normalizes any string or enum to a canonical VisualType."""
        if isinstance(raw_type, VisualType):
            return raw_type
        if not raw_type:
            return None
        cleaned = str(raw_type).strip().upper().replace(" ", "_").replace("-", "_")
        for vt in VisualType:
            if vt.value == cleaned:
                return vt
        # Alias matching
        alias_map = {
            "MAPS": VisualType.MAP,
            "ROUTE_MAP": VisualType.MAP_ANIMATION,
            "CHART": VisualType.DATA_CHART,
            "GRAPH": VisualType.DATA_CHART,
            "NUMBER_GRAPHIC": VisualType.DATA_CHART,
            "STATISTIC": VisualType.DATA_CHART,
            "EVIDENCE": VisualType.AUTHENTIC_EVIDENCE,
            "DOSSIER": VisualType.AUTHENTIC_EVIDENCE,
            "ARCHIVE": VisualType.REAL_ARCHIVAL,
            "ARCHIVAL": VisualType.REAL_ARCHIVAL,
            "PHOTO": VisualType.PHOTOGRAPH,
            "AI_CLIP": VisualType.AI_IMAGE_TO_VIDEO,
            "AI_VIDEO": VisualType.AI_VIDEO,
            "AI_STILL": VisualType.AI_IMAGE,
            "BROLL": VisualType.STOCK_BROLL,
            "STOCK": VisualType.STOCK_BROLL,
            "ATMOSPHERE": VisualType.ATMOSPHERIC_VISUAL,
            "RADAR": VisualType.SCREEN_RECREATION,
            "HUD": VisualType.SCREEN_RECREATION,
        }
        return alias_map.get(cleaned, None)

    @classmethod
    def is_supported(cls, vtype: VisualType | str) -> bool:
        norm = cls.normalize_type(vtype)
        return norm in SUPPORTED_NOW if norm else False

    @classmethod
    def is_planned(cls, vtype: VisualType | str) -> bool:
        norm = cls.normalize_type(vtype)
        return norm in PLANNED if norm else False

    @classmethod
    def get_supported_types(cls) -> List[str]:
        return [vt.value for vt in SUPPORTED_NOW]

    @classmethod
    def get_default_provider(cls, vtype: VisualType | str) -> str:
        norm = cls.normalize_type(vtype)
        if norm and norm in DEFAULT_PROVIDER_MAPPING:
            return DEFAULT_PROVIDER_MAPPING[norm]
        return "browser_flow"

    @classmethod
    def resolve_fallback_chain(cls, vtype: VisualType | str) -> List[VisualType]:
        """Returns the ordered semantic fallback chain for a visual type."""
        norm = cls.normalize_type(vtype)
        if not norm:
            return [VisualType.STOCK_BROLL, VisualType.ATMOSPHERIC_VISUAL]
        chain = SEMANTIC_FALLBACKS.get(norm, [])
        # Only return fallbacks that are currently supported
        return [fb for fb in chain if fb in SUPPORTED_NOW]

    @classmethod
    def get_cost_profile(cls, vtype: VisualType | str) -> Tuple[CostClass, ComputeClass, float]:
        """Returns (CostClass, ComputeClass, estimated_generation_seconds)."""
        norm = cls.normalize_type(vtype)
        if not norm:
            return CostClass.LOW, ComputeClass.LOCAL, 1.0

        if norm in (VisualType.AI_VIDEO, VisualType.AI_IMAGE_TO_VIDEO):
            return CostClass.HIGH, ComputeClass.BROWSER, 15.0
        elif norm in (VisualType.AI_IMAGE, VisualType.BROWSER_GENERATED_VISUAL):
            return CostClass.MEDIUM, ComputeClass.BROWSER, 4.0
        elif norm in (VisualType.MAP, VisualType.MAP_ANIMATION, VisualType.DATA_CHART, VisualType.AUTHENTIC_EVIDENCE, VisualType.TIMELINE_DIAGRAM):
            return CostClass.FREE_PROCEDURAL, ComputeClass.LOCAL, 2.0
        else:
            return CostClass.LOW, ComputeClass.LOCAL, 0.5
