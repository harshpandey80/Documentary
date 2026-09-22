"""
DocStudio Visual Director Strategies & Authenticity Models.
Defines all supported semantic visual strategies, authenticity statuses,
and multi-layer composition roles.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Any


class VisualStrategy(str, Enum):
    # Narrative & Cinematic Reconstructions
    HUMAN_RECONSTRUCTION = "HUMAN_RECONSTRUCTION"
    AI_CINEMATIC_VIDEO = "AI_CINEMATIC_VIDEO"
    AI_CINEMATIC_STILL = "AI_CINEMATIC_STILL"
    OBJECT_RECONSTRUCTION = "OBJECT_RECONSTRUCTION"
    PARALLAX_IMAGE = "PARALLAX_IMAGE"

    # Historical & Primary Archives
    ARCHIVAL_PHOTO = "ARCHIVAL_PHOTO"
    ARCHIVAL_VIDEO = "ARCHIVAL_VIDEO"
    PRIMARY_DOCUMENT = "PRIMARY_DOCUMENT"
    NEWSPAPER = "NEWSPAPER"

    # Geospatial & Tactical
    MAP = "MAP"
    ROUTE_MAP = "ROUTE_MAP"
    GEOGRAPHICAL_SCALE = "GEOGRAPHICAL_SCALE"
    LOCATION_ESTABLISHING = "LOCATION_ESTABLISHING"

    # Data & Numerical Analytics
    TIMELINE = "TIMELINE"
    DATA_CHART = "DATA_CHART"
    STATISTIC = "STATISTIC"
    COMPARISON = "COMPARISON"
    BEFORE_AFTER = "BEFORE_AFTER"

    # Diagrammatic & Relational Systems
    DIAGRAM = "DIAGRAM"
    FLOW_DIAGRAM = "FLOW_DIAGRAM"
    ORG_CHART = "ORG_CHART"
    EVIDENCE_BOARD = "EVIDENCE_BOARD"
    CONNECTION_GRAPH = "CONNECTION_GRAPH"
    EVIDENCE_MATRIX = "EVIDENCE_MATRIX"
    CAUSE_EFFECT = "CAUSE_EFFECT"

    # Digital & Document Forensics
    SCREEN_RECREATION = "SCREEN_RECREATION"
    WEBSITE_RECREATION = "WEBSITE_RECREATION"
    SOCIAL_MEDIA_RECREATION = "SOCIAL_MEDIA_RECREATION"
    DATABASE_LOOKUP = "DATABASE_LOOKUP"
    DOCUMENT_HIGHLIGHT = "DOCUMENT_HIGHLIGHT"
    QUOTE_CARD = "QUOTE_CARD"
    LOCATION_CARD = "LOCATION_CARD"

    # Typography & Atmosphere
    KINETIC_TYPOGRAPHY = "KINETIC_TYPOGRAPHY"
    ATMOSPHERIC_BROLL = "ATMOSPHERIC_BROLL"
    STOCK_VIDEO = "STOCK_VIDEO"
    ABSTRACT_MOTION = "ABSTRACT_MOTION"


class VisualStatus(str, Enum):
    """
    Authenticity label for documentary integrity.
    Prevents synthetic fabrications from being presented as real records.
    """
    AUTHENTIC_SOURCE = "AUTHENTIC_SOURCE"   # Verified real historical document, photo, or recording
    RECONSTRUCTION = "RECONSTRUCTION"       # Dramatic reenactment or simulated interface (labeled as reconstruction)
    AI_GENERATED = "AI_GENERATED"           # High-impact synthetic generative visual / video
    PROCEDURAL = "PROCEDURAL"               # Procedural code-rendered map, data chart, or HUD
    STOCK = "STOCK"                         # Licensed or open stock video / B-roll
    ARCHIVAL = "ARCHIVAL"                   # Public domain historical archive scan


class VisualLayer(str, Enum):
    """
    Layer definition for multi-layered compositions (Section 15).
    """
    BACKGROUND = "BACKGROUND"
    PRIMARY_VISUAL = "PRIMARY_VISUAL"
    SECONDARY_EVIDENCE = "SECONDARY_EVIDENCE"
    ANNOTATION = "ANNOTATION"
    MAP = "MAP"
    TIMELINE = "TIMELINE"
    TYPOGRAPHY = "TYPOGRAPHY"
    TEXTURE = "TEXTURE"
    LIGHTING = "LIGHTING"
    SUBTLE_EFFECTS = "SUBTLE_EFFECTS"


STRATEGY_NAMES: List[str] = [s.value for s in VisualStrategy]

# Grouping strategies by engine category
GRAPHIC_STRATEGIES = {
    VisualStrategy.MAP,
    VisualStrategy.ROUTE_MAP,
    VisualStrategy.GEOGRAPHICAL_SCALE,
    VisualStrategy.TIMELINE,
    VisualStrategy.DATA_CHART,
    VisualStrategy.STATISTIC,
    VisualStrategy.COMPARISON,
    VisualStrategy.BEFORE_AFTER,
    VisualStrategy.DIAGRAM,
    VisualStrategy.FLOW_DIAGRAM,
    VisualStrategy.ORG_CHART,
    VisualStrategy.EVIDENCE_BOARD,
    VisualStrategy.CONNECTION_GRAPH,
    VisualStrategy.EVIDENCE_MATRIX,
    VisualStrategy.CAUSE_EFFECT,
    VisualStrategy.DOCUMENT_HIGHLIGHT,
    VisualStrategy.QUOTE_CARD,
    VisualStrategy.LOCATION_CARD,
    VisualStrategy.DATABASE_LOOKUP,
    VisualStrategy.KINETIC_TYPOGRAPHY,
}

AI_VIDEO_STRATEGIES = {
    VisualStrategy.AI_CINEMATIC_VIDEO,
    VisualStrategy.HUMAN_RECONSTRUCTION,
    VisualStrategy.OBJECT_RECONSTRUCTION,
}

ARCHIVAL_STRATEGIES = {
    VisualStrategy.ARCHIVAL_PHOTO,
    VisualStrategy.ARCHIVAL_VIDEO,
    VisualStrategy.PRIMARY_DOCUMENT,
    VisualStrategy.NEWSPAPER,
}
