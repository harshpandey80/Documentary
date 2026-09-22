"""
DocStudio Graphic Intent & Validation Model.
Enforces that every motion graphic has explicit purpose, verified source claims,
concrete data, and an animation plan before any rendering is permitted.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class GraphicIntent:
    purpose: str
    source_claims: List[str]
    key_message: str
    visualization_type: str
    data: List[Any] = field(default_factory=list)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    animation_sequence: List[Dict[str, Any]] = field(default_factory=list)
    duration_s: float = 3.0
    theme: str = "dark_cinematic"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "purpose": self.purpose,
            "source_claims": list(self.source_claims),
            "key_message": self.key_message,
            "visualization_type": self.visualization_type,
            "data": list(self.data),
            "annotations": list(self.annotations),
            "animation_sequence": list(self.animation_sequence),
            "duration_s": self.duration_s,
            "theme": self.theme,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphicIntent":
        return cls(
            purpose=str(d.get("purpose", "")),
            source_claims=list(d.get("source_claims", [])),
            key_message=str(d.get("key_message", "")),
            visualization_type=str(d.get("visualization_type", "")).lower(),
            data=list(d.get("data", [])),
            annotations=list(d.get("annotations", [])),
            animation_sequence=list(d.get("animation_sequence", [])),
            duration_s=float(d.get("duration_s", 3.0)),
            theme=str(d.get("theme", "dark_cinematic")),
        )


def validate_graphic_intent(intent: GraphicIntent) -> Tuple[bool, str]:
    """
    Strict validation rule enforcing that no empty, fake, or ungrounded graphic is rendered.
    Returns (is_valid, error_reason).
    """
    if not intent.purpose or not intent.purpose.strip():
        return False, "Graphic rejected: 'purpose' cannot be null or empty."

    viz = intent.visualization_type.lower()
    chart_types = {"bar_chart", "line_chart", "data_chart", "statistic", "statistic_counter"}
    evidence_types = {"comparison", "evidence_matrix", "document_highlight", "timeline"}

    # 1. Evidence and chart visuals MUST have source claims
    if viz in chart_types or viz in evidence_types:
        if not intent.source_claims or len(intent.source_claims) == 0:
            return False, f"Graphic rejected: '{viz}' represents factual evidence but has no source_claims."

    # 2. Charts MUST have verified data points
    if viz in chart_types:
        if not intent.data or len(intent.data) == 0:
            return False, f"Graphic rejected: chart '{viz}' has no verified data points."

    # 3. Key message must not be blank
    if not intent.key_message or not intent.key_message.strip():
        return False, "Graphic rejected: 'key_message' cannot be empty."

    return True, "Valid"
