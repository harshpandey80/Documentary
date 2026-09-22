"""
DocStudio Visual Continuity Engine.
Maintains consistent visual character identities, persistent locations,
period-accurate props, lighting tokens, and camera language across scenes.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional


class VisualContinuityTracker:
    """
    Ensures that when characters, locations, or recurring objects appear across multiple scenes,
    their visual descriptions, wardrobe, lighting, and era attributes remain coherent.
    """

    def __init__(self, topic: str):
        self.topic = topic
        self.characters: Dict[str, Dict[str, Any]] = {}
        self.locations: Dict[str, Dict[str, Any]] = {}
        self.recurring_objects: Dict[str, Dict[str, Any]] = {}
        self.era_bible = self._init_era_bible(topic)

    def _init_era_bible(self, topic: str) -> Dict[str, str]:
        t = topic.lower()
        if any(w in t for w in ["1940", "1945", "ww2", "world war", "bomber", "aviation", "navy"]):
            return {
                "period": "1940s Mid-Century Naval Aviation",
                "color_palette": "muted olive drab, desaturated navy blue, tungsten amber, deep silver blacks",
                "film_stock": "Kodak Tri-X 35mm grain with gentle silver halide halation",
                "lighting_language": "dramatic chiaroscuro, volumetric mist, motivated cockpit dial illumination",
                "camera_style": "vintage 35mm anamorphic prime lens, subtle handheld inertia",
            }
        elif any(w in t for w in ["space", "apollo", "moon", "nasa", "orbit"]):
            return {
                "period": "1960s-1970s Space Age",
                "color_palette": "deep void black, oxygen tank white, solar gold, telemetry cyan",
                "film_stock": "Hasselblad 70mm transparency film, crisp contrast",
                "lighting_language": "harsh unfiltered solar keylight, vacuum shadow cutoff",
                "camera_style": "scientific reconnaissance lens, slow orbital tracking",
            }
        elif any(w in t for w in ["cold war", "soviet", "kgb", "cia", "berlin", "1970", "1980"]):
            return {
                "period": "Cold War Espionage Era",
                "color_palette": "concrete gray, fluorescent teal, faded microfilm amber",
                "film_stock": "16mm surveillance negative grain",
                "lighting_language": "harsh institutional fluorescent, deep interrogation shadows",
                "camera_style": "surveillance telephoto lens, slow push through architectural frames",
            }
        else:
            return {
                "period": "Modern Investigative Documentary",
                "color_palette": "naturalistic modern cinema, neutral cool tones, rich shadow detail",
                "film_stock": "Arri Alexa LF 4K cinematic grain",
                "lighting_language": "motivated soft natural lighting with rim key",
                "camera_style": "high-precision cinema gimbal, smooth controlled push-ins",
            }

    def register_character(
        self,
        name: str,
        appearance: str,
        role: str = "",
        wardrobe: str = "",
        age_range: str = "",
    ) -> None:
        key = name.lower().strip()
        self.characters[key] = {
            "name": name,
            "appearance": appearance,
            "role": role,
            "wardrobe": wardrobe,
            "age_range": age_range,
        }

    def register_location(
        self,
        name: str,
        visual_attributes: str,
        lighting: str = "",
    ) -> None:
        key = name.lower().strip()
        self.locations[key] = {
            "name": name,
            "visual_attributes": visual_attributes,
            "lighting": lighting,
        }

    def enrich_prompt(self, base_prompt: str, scene_context: str = "") -> str:
        """
        Enriches an image or video generation prompt with persistent character identities,
        location anchors, and era cinematography directives.
        """
        combined = f"{base_prompt} {scene_context}".lower()
        matched_tokens: List[str] = []

        # Check character continuity
        for key, char in self.characters.items():
            if key in combined:
                desc = f"{char['name']} ({char['age_range']}, {char['appearance']}, wearing {char['wardrobe']})"
                matched_tokens.append(desc)

        # Check location continuity
        for key, loc in self.locations.items():
            if key in combined:
                desc = f"at {loc['name']} ({loc['visual_attributes']})"
                matched_tokens.append(desc)

        # Assemble unified prompt
        bible = self.era_bible
        cinematography = f"{bible['lighting_language']}, {bible['color_palette']}, {bible['film_stock']}, {bible['camera_style']}"

        continuity_prefix = ""
        if matched_tokens:
            continuity_prefix = f"Consistent subject: {'; '.join(matched_tokens)}. "

        return f"{continuity_prefix}{base_prompt}, {cinematography}, masterclass documentary production value"
