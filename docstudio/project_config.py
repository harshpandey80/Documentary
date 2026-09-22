"""
DocStudio Project Configuration Model and Schema Validator.
Encapsulates all topic-specific, editorial, pacing, and visual directives in a single project.yaml.
Zero topic hardcoding allowed in code.
"""

from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import yaml

@dataclass
class StyleProfile:
    font_primary: str = "Montserrat"
    font_accent: str = "Cinzel"
    color_primary: str = "#FFFFFF"
    color_accent: str = "#00FF66"  # Active highlight (Hormozi neon green)
    color_bg: str = "#080C10"      # Deep matte obsidian
    easing: str = "ease_out_cubic"
    caption_style: str = "hormozi_kinetic"

    # Aliases for flexibility
    @property
    def font_family(self) -> str:
        return self.font_primary

    @property
    def title_font(self) -> str:
        return self.font_accent

    @property
    def primary_color(self) -> str:
        return self.color_primary

    @property
    def accent_color(self) -> str:
        return self.color_accent

    @property
    def bg_color(self) -> str:
        return self.color_bg

@dataclass
class ProjectConfig:
    topic: str
    thesis: str
    audience: str = "Curious investigative documentary viewers"
    tone: str = "Investigative, factual, atmospheric, urgent"
    runtime: str = "5m"
    aspect_ratio: str = "16:9"
    cut_length: float = 3.0
    tts_engine: str = "voxcpm"
    visual_tiers: List[str] = field(default_factory=lambda: ["archival", "ai_hero", "code2video", "stock"])
    all_ai_visuals: bool = True
    style_profile: StyleProfile = field(default_factory=StyleProfile)
    graphic_budget: int = 20  # Maximum number graphics permitted per video
    allow_unverified_claims: bool = False
    custom_telemetry: Dict[str, Any] = field(default_factory=dict)
    color_grade_preset: str = "kodak_2383"
    question: Optional[str] = None
    answer_claim_id: Optional[str] = None
    twist: Optional[str] = None
    script_path: Optional[str] = None
    
    def __post_init__(self):
        # Validate aspect ratio
        if self.aspect_ratio not in ["16:9", "9:16"]:
            raise ValueError(f"Invalid aspect_ratio '{self.aspect_ratio}'. Must be '16:9' or '9:16'.")
        
        # Validate cut_length (must be between 0.5s and 10.0s)
        if self.cut_length < 0.5 or self.cut_length > 10.0:
            raise ValueError(f"Cut length {self.cut_length}s is outside valid range (0.5s - 10.0s).")
            
        # Parse runtime into seconds
        self.runtime_seconds = self.parse_runtime_seconds(self.runtime)
        
        # Expected cut count
        self.expected_cuts = int(round(self.runtime_seconds / self.cut_length))

    @property
    def target_cuts(self) -> int:
        return self.expected_cuts

    @property
    def is_short(self) -> bool:
        return self.aspect_ratio == "9:16" or self.runtime_seconds <= 90.0

    @property
    def width(self) -> int:
        return 1080 if self.aspect_ratio == "9:16" else 1920

    @property
    def height(self) -> int:
        return 1920 if self.aspect_ratio == "9:16" else 1080

    @staticmethod
    def parse_runtime_seconds(runtime_str: str) -> float:
        """Parses human runtime string (e.g., '60s', '5m', '8m', '10m', '180') into seconds."""
        s = str(runtime_str).strip().lower()
        if s.endswith("m"):
            return float(s[:-1]) * 60.0
        elif s.endswith("s"):
            return float(s[:-1])
        try:
            return float(s)
        except ValueError:
            raise ValueError(f"Cannot parse runtime '{runtime_str}'. Expected format like '60s', '5m', '8m'.")

    @property
    def resolution(self) -> tuple[int, int]:
        """Returns (width, height) based on aspect ratio."""
        return (self.width, self.height)


def load_project_config(path_or_str: str | Path) -> ProjectConfig:
    """Loads and validates a project configuration from a YAML file or raw string."""
    p = Path(path_or_str)
    if p.exists() and p.is_file():
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    else:
        # Attempt to parse as raw YAML string
        data = yaml.safe_load(str(path_or_str)) or {}

    if not isinstance(data, dict):
        raise ValueError("Project configuration must be a valid mapping / dictionary.")

    topic = data.get("topic")
    thesis = data.get("thesis")
    if not topic or not str(topic).strip():
        raise ValueError("Missing required configuration field: 'topic'")
    if not thesis or not str(thesis).strip():
        raise ValueError("Missing required configuration field: 'thesis'")

    style_data = data.get("style_profile", {})
    if not isinstance(style_data, dict):
        style_data = {}
        
    style = StyleProfile(
        font_primary=style_data.get("font_primary", "Montserrat"),
        font_accent=style_data.get("font_accent", "Cinzel"),
        color_primary=style_data.get("color_primary", "#FFFFFF"),
        color_accent=style_data.get("color_accent", "#00FF66"),
        color_bg=style_data.get("color_bg", "#080C10"),
        easing=style_data.get("easing", "ease_out_cubic"),
    )

    return ProjectConfig(
        topic=str(topic).strip(),
        thesis=str(thesis).strip(),
        audience=data.get("audience", "Curious investigative documentary viewers"),
        tone=data.get("tone", "Investigative, factual, atmospheric, urgent"),
        runtime=str(data.get("runtime", "5m")),
        aspect_ratio=str(data.get("aspect_ratio", "16:9")),
        cut_length=float(data.get("cut_length", 3.0)),
        tts_engine=str(data.get("tts_engine", "voxcpm")),
        visual_tiers=data.get("visual_tiers", ["archival", "ai_hero", "code2video", "stock"]),
        all_ai_visuals=bool(data.get("all_ai_visuals", True)),
        style_profile=style,
        graphic_budget=int(data.get("graphic_budget", 20)),
        allow_unverified_claims=bool(data.get("allow_unverified_claims", False)),
        custom_telemetry=data.get("custom_telemetry", {}),
        color_grade_preset=data.get("color_grade_preset", "kodak_2383"),
        question=data.get("question"),
        answer_claim_id=data.get("answer_claim_id"),
        twist=data.get("twist"),
        script_path=data.get("script_path"),
    )


def save_project_config(config: ProjectConfig, path: Path | str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "topic": config.topic,
        "thesis": config.thesis,
        "audience": config.audience,
        "tone": config.tone,
        "runtime": config.runtime,
        "aspect_ratio": config.aspect_ratio,
        "cut_length": config.cut_length,
        "tts_engine": config.tts_engine,
        "visual_tiers": config.visual_tiers,
        "all_ai_visuals": config.all_ai_visuals,
        "style_profile": {
            "font_family": config.style_profile.font_family,
            "title_font": config.style_profile.title_font,
            "primary_color": config.style_profile.primary_color,
            "accent_color": config.style_profile.accent_color,
            "bg_color": config.style_profile.bg_color,
            "easing": config.style_profile.easing,
            "caption_style": config.style_profile.caption_style,
        },
        "graphic_budget": config.graphic_budget,
        "allow_unverified_claims": config.allow_unverified_claims,
        "custom_telemetry": config.custom_telemetry,
    }
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False)


def create_default_project_yaml(
    dest_path: Path | str,
    topic: str = "Unexplained Event",
    thesis: str = "An investigative breakdown.",
) -> Path:
    cfg = ProjectConfig(topic=topic, thesis=thesis)
    p = Path(dest_path)
    save_project_config(cfg, p)
    return p

