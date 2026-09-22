"""
DocStudio Visual Director Package.
Autonomous directorial framework for semantic visual classification,
multi-shot scene storyboarding, multi-layer compositions, and continuity.
"""

from docstudio.visual_director.strategies import (
    VisualStrategy,
    VisualStatus,
    VisualLayer,
    STRATEGY_NAMES,
)
from docstudio.visual_director.classifier import SemanticVisualClassifier
from docstudio.visual_director.storyboard import ShotStoryboardGenerator
from docstudio.visual_director.continuity import VisualContinuityTracker
from docstudio.visual_director.director import VisualDirector

__all__ = [
    "VisualStrategy",
    "VisualStatus",
    "VisualLayer",
    "STRATEGY_NAMES",
    "SemanticVisualClassifier",
    "ShotStoryboardGenerator",
    "VisualContinuityTracker",
    "VisualDirector",
]
