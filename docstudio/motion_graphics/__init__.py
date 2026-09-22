"""
DocStudio Motion Graphics Rebuild Package.
Autonomous evidence visualization and purposeful motion graphics generation.
"""

from docstudio.motion_graphics.graphic_intent import (
    GraphicIntent,
    validate_graphic_intent,
)
from docstudio.motion_graphics.dispatcher import MotionGraphicsDispatcher

__all__ = [
    "GraphicIntent",
    "validate_graphic_intent",
    "MotionGraphicsDispatcher",
]
