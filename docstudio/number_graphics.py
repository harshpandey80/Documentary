"""
Number Graphics Engine - Deterministic Non-LLM Numeric Visualizer
------------------------------------------------------------------
Detects quantities, classifications, and comparative claims without an LLM.
Enforces broadcast motion rules:
  - Ease-out for counting/progress (lands exactly as number is spoken)
  - Ease-in-out for fades (~0.3s in, ~0.3s out, 1.0s hold after speech)
  - 15-second minimum interval pacing rule
  - Sourced, hand-checked human anchors comparison library (zero invented comparisons)
  - Deterministic caching to skip redundant renders
  - 6 Core Graphic Archetypes:
      1. Percentage -> Ring (radial progress donut)
      2. Four-digit year -> Timeline (historical era marker)
      3. Length/depth/height units -> Gauge (vertical scale with human anchor)
      4. Money or large counts -> Count-up (HUD counter panel)
      5. "N times" or "than" -> Comparison (dual-bar comparative visual)
      6. "1 in N" -> Dot Grid (matrix with highlighted target fraction)
"""

from __future__ import annotations

import csv
import math
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ==============================================================================
# 1. GRAPHIC TYPES & DATA STRUCTURES
# ==============================================================================

class GraphicType(str, Enum):
    RING = "ring"              # Percentage -> radial donut progress ring
    TIMELINE = "timeline"      # 4-digit year -> historical era timeline
    GAUGE = "gauge"            # Length, depth, height units -> vertical gauge
    COUNTUP = "countup"        # Money or large counts -> eased count-up HUD
    COMPARISON = "comparison"  # "N times" or "than" -> dual-bar comparative visual
    DOT_GRID = "dot_grid"      # "1 in N" -> matrix of dots with illuminated fraction


@dataclass
class HumanAnchor:
    name: str
    value: float
    unit: str
    source: str
    notes: str = ""


@dataclass
class DetectedGraphic:
    graphic_type: GraphicType
    raw_text: str
    numeric_value: float
    unit: str = ""
    label: str = ""
    subtitle: str = ""
    human_anchor: Optional[HumanAnchor] = None
    confidence: float = 1.0
    source_claim_id: Optional[str] = None
    # Timing fields populated when aligned with word timestamps
    start_time: float = 0.0
    spoken_land_time: float = 0.0
    duration: float = 3.2
    count_time: float = 1.6
    hold_time: float = 1.0
    fade_time: float = 0.3


# ==============================================================================
# 2. HAND-CHECKED HUMAN ANCHOR LIBRARY
# ==============================================================================
# Sourced, verified reference objects with documented dimensions.
# Code selects the nearest scale. Nothing invents or hallucinates comparisons.

HUMAN_ANCHORS: Dict[str, List[HumanAnchor]] = {
    "length_depth": [
        HumanAnchor("Human Height", 1.8, "m", "Standard anthropometry (6 ft)", "Standing adult human"),
        HumanAnchor("School Bus Length", 12.0, "m", "US DOT Federal Motor Vehicle Safety Standards", "Standard transit bus"),
        HumanAnchor("Blue Whale Length", 30.0, "m", "NOAA Fisheries Marine Mammal Database", "Largest animal on Earth"),
        HumanAnchor("Boeing 747-400 Wingspan", 64.4, "m", "Boeing Aircraft Specifications", "Commercial jumbo jet"),
        HumanAnchor("Boeing 747 Length", 70.6, "m", "Boeing Aircraft Specifications", "Cruising airliner"),
        HumanAnchor("Statue of Liberty Height", 93.0, "m", "National Park Service Archives", "Pedestal to torch"),
        HumanAnchor("Eiffel Tower Height", 330.0, "m", "SETE Paris Official Architecture", "Historic iron lattice tower"),
        HumanAnchor("Burj Khalifa Height", 828.0, "m", "Emaar Properties Engineering", "Tallest architectural structure"),
        HumanAnchor("Mount Everest Summit", 8848.0, "m", "Survey of Nepal / China 2020", "Highest terrestrial peak"),
        HumanAnchor("Commercial Cruising Altitude", 10668.0, "m", "FAA Flight Level Standards (FL350 / 35,000 ft)", "Airliner cruising altitude"),
        HumanAnchor("Ocean Hadal Trench Floor", 10984.0, "m", "NOAA / UNH Multibeam Bathymetry (36,037 ft)", "Deepest ocean abyss on Earth"),
        HumanAnchor("Distance London to Paris", 343000.0, "m", "Ordnance Survey (343 km / 213 mi)", "Straight line channel distance"),
        HumanAnchor("Distance London to Rome", 1435000.0, "m", "European Cartographic Survey (1,435 km / 892 mi)", "Continental European span"),
        HumanAnchor("Mariana Trench Arc Length", 2550000.0, "m", "NOAA NCEI Bathymetry (2,550 km)", "Total crescent trench arc"),
    ],
    "money": [
        HumanAnchor("Average Annual Worker Salary", 60000.0, "$", "Bureau of Labor Statistics", "Single worker annual wage"),
        HumanAnchor("Median US Home Price", 412000.0, "$", "Federal Reserve FRED (Q4 2023)", "Single-family residential home"),
        HumanAnchor("Hollywood Blockbuster Film Budget", 200000000.0, "$", "Box Office Mojo Verified Film Records", "Major theatrical production"),
        HumanAnchor("Nimitz-Class Aircraft Carrier", 8500000000.0, "$", "US Congressional Budget Office", "Naval capital ship"),
        HumanAnchor("NASA Annual Budget", 25000000000.0, "$", "NASA Congressional Justification 2024", "National space agency annual funding"),
        HumanAnchor("United Kingdom Annual GDP", 3100000000000.0, "$", "World Bank National Accounts 2023", "National economic output"),
    ],
    "population_count": [
        HumanAnchor("Imperial Roman Legion", 5000.0, "people", "Oxford Classical Dictionary", "Standard heavy infantry legion"),
        HumanAnchor("Modern Army Division", 15000.0, "people", "Military Doctrine Standards", "Combined arms division"),
        HumanAnchor("Wembley Stadium Full Capacity", 90000.0, "people", "Wembley Stadium Official Records", "Major international stadium"),
        HumanAnchor("London Population in 1800", 1000000.0, "people", "UK National Census Historical Records", "First city of 1M in modern era"),
        HumanAnchor("British Empire Peak Population", 412000000.0, "people", "Historical Statistics of the British Empire (1920)", "One-fifth of humanity in 1920"),
        HumanAnchor("Global Population in 1920", 1860000000.0, "people", "UN Population Division Historical Estimates", "Total planetary population"),
    ],
}


def normalize_to_meters(value: float, unit: str) -> float:
    """Normalize length/depth/height unit to meters for comparison matching."""
    u = unit.lower().strip()
    if u in ("m", "meter", "meters", "metre", "metres"):
        return value
    if u in ("ft", "foot", "feet"):
        return value * 0.3048
    if u in ("km", "kilometer", "kilometers", "kilometre", "kilometres"):
        return value * 1000.0
    if u in ("mi", "mile", "miles"):
        return value * 1609.34
    if u in ("fathom", "fathoms"):
        return value * 1.8288
    if u in ("in", "inch", "inches"):
        return value * 0.0254
    if u in ("yd", "yard", "yards"):
        return value * 0.9144
    return value


def get_nearest_human_anchor(value: float, unit: str = "") -> Optional[HumanAnchor]:
    """
    Picks the nearest sourced human anchor scale by code using log-ratio distance.
    Guarantees that comparisons are purely sourced from verified reality.
    """
    if value <= 0:
        return None

    category = "length_depth"
    comp_value = value

    unit_clean = unit.lower().strip()
    if any(m in unit_clean for m in ("$", "£", "€", "usd", "dollar", "pound", "euro", "wealth", "budget", "cost")):
        category = "money"
    elif any(p in unit_clean for p in ("people", "soldier", "population", "citizen", "troop", "casualt")):
        category = "population_count"
    elif any(d in unit_clean for d in ("m", "meter", "metre", "ft", "feet", "foot", "km", "mile", "fathom", "inch", "depth", "altitude", "height", "length")):
        category = "length_depth"
        comp_value = normalize_to_meters(value, unit)
    else:
        # Infer based on magnitude if unit is ambiguous
        if comp_value > 5000 and comp_value < 1000000:
            category = "population_count"
        else:
            category = "length_depth"

    anchors = HUMAN_ANCHORS.get(category, [])
    if not anchors:
        return None

    # Find closest by ratio in log space: |log(comp_value) - log(anchor.value)|
    best_anchor = None
    best_dist = float("inf")
    for anchor in anchors:
        dist = abs(math.log10(max(1e-9, comp_value)) - math.log10(max(1e-9, anchor.value)))
        if dist < best_dist:
            best_dist = dist
            best_anchor = anchor

    return best_anchor


# ==============================================================================
# 3. NON-LLM DETECTION & CLASSIFICATION ENGINE
# ==============================================================================

class NumberGraphicDetector:
    """
    Deterministic rule-based detector for numeric graphics without an LLM.
    Uses regex and grammatical structure to classify quantities into 6 archetypes.
    """

    # Compiled regex patterns
    RE_PERCENT = re.compile(r'(\d+(?:\.\d+)?)\s*(?:%|percent(?:age)?\b)', re.IGNORECASE)
    RE_DOT_GRID = re.compile(r'\b(?:1|one)\s+in\s+(\d+|[a-zA-Z]+)\b|\b(\d+)\s+in\s+(\d+)\b', re.IGNORECASE)
    RE_COMPARISON = re.compile(
        r'\b(\d+(?:\.\d+)?)\s*(?:x|times)\s+(?:more|less|greater|larger|deeper|faster|higher)?\b|'
        r'\b(?:more|less|greater|faster|deeper|larger|higher)\s+than\s+(\d+(?:\.\d+)?)\b',
        re.IGNORECASE
    )
    RE_YEAR = re.compile(r'\b(?:in\s+)?(1\d{3}|20\d{2})\b|\bAD\s*(\d{1,4})\b|\b(\d{1,4})\s*BC\b', re.IGNORECASE)
    RE_DIMENSION = re.compile(
        r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*'
        r'(meters?|metres?|feet|ft|kilometers?|kilometres?|km|miles?|fathoms?|inches?|yards?)\b',
        re.IGNORECASE
    )
    RE_MONEY = re.compile(
        r'[\$£€]\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(billion|million|thousand|trillion|k|m|b)?(?!\w)|'
        r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:dollars?|pounds?|euros?)\b',
        re.IGNORECASE
    )
    RE_LARGE_COUNT = re.compile(
        r'\b(\d{1,3}(?:,\d{3})+(?:\.\d+)?)\b|\b(\d+(?:\.\d+)?)\s*(million|billion|trillion)\b',
        re.IGNORECASE
    )

    # Word-to-number mapping for conversational fractions
    WORD_NUMBERS = {
        "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twenty": 20, "fifty": 50, "hundred": 100, "thousand": 1000
    }

    def detect_from_claims_file(self, ledger_path: Union[Path, str] = "claims.csv") -> List[DetectedGraphic]:
        """
        Simplest and most reliable: read directly from claims file where graphic entries
        are explicitly defined with verifiable numbers and units.
        """
        p = Path(ledger_path)
        if not p.exists():
            return []

        graphics: List[DetectedGraphic] = []
        with open(p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                is_worthy = row.get("graphic_worthy", "").strip().lower() in ("yes", "true", "1")
                if not is_worthy:
                    continue

                cid = row.get("ID", "").strip()
                claim_text = row.get("claim", "").strip()
                num_str = row.get("number/date", "").strip()
                unit = row.get("unit", "").strip()
                anchor_text = row.get("human_anchor", "").strip()

                # Parse numerical value
                clean_num_str = re.sub(r"[^\d.]", "", num_str.replace(",", ""))
                try:
                    num_val = float(clean_num_str) if clean_num_str else 0.0
                except ValueError:
                    num_val = 0.0

                # Type classification rules per spec
                gtype = self.classify_type(num_str, unit, claim_text)
                anchor = get_nearest_human_anchor(num_val, unit)
                if anchor_text and anchor:
                    anchor.notes = anchor_text

                label = claim_text[:40].upper()
                graphics.append(DetectedGraphic(
                    graphic_type=gtype,
                    raw_text=f"{num_str} {unit}".strip(),
                    numeric_value=num_val,
                    unit=unit,
                    label=label,
                    subtitle=anchor_text or (anchor.name if anchor else ""),
                    human_anchor=anchor,
                    source_claim_id=cid,
                ))

        return graphics

    def classify_type(self, value_str: str, unit: str, context_text: str = "") -> GraphicType:
        """
        Strict non-LLM Type Rules:
          - A percentage becomes a ring.
          - A four-digit year becomes a timeline.
          - Length, depth, or height units become a gauge.
          - Money or large counts become a count-up.
          - "N times" or "than" becomes a comparison.
          - "1 in N" becomes a dot grid.
        """
        full_text = f"{value_str} {unit} {context_text}".lower()

        # 1. Percentage -> Ring
        if "%" in value_str or "%" in unit or "percent" in unit.lower() or "percent" in context_text.lower():
            return GraphicType.RING

        # 2. "1 in N" -> Dot Grid
        if " in " in full_text and any(x in full_text for x in ("1 in", "one in")):
            return GraphicType.DOT_GRID

        # 3. "N times" or "than" -> Comparison
        if "times" in full_text or "than" in full_text or re.search(r'\b\d+(?:\.\d+)?x\b', full_text):
            return GraphicType.COMPARISON

        # 4. Length, depth, height units -> Gauge
        gauge_units = ("meter", "meters", "metre", "metres", "m", "feet", "ft", "foot", "km", "kilometer",
                       "kilometre", "mile", "miles", "fathom", "fathoms", "inch", "inches", "depth", "height", "altitude")
        if any(u == unit.lower().strip() for u in gauge_units) or any(f" {u}" in full_text for u in gauge_units):
            return GraphicType.GAUGE

        # 5. Four-digit year -> Timeline
        clean_num = re.sub(r"[^\d]", "", value_str)
        if (len(clean_num) == 4 and 900 <= int(clean_num) <= 2100) or unit.lower() in ("date", "year", "ad", "bc"):
            return GraphicType.TIMELINE

        # 6. Money or large counts -> Count-up
        return GraphicType.COUNTUP

    def detect_from_text(self, text: str) -> List[DetectedGraphic]:
        """
        Automatic detection: regular expressions + small statistical/lexical pipeline.
        Recognizes quantities, money, percentages, dates, and comparisons without an LLM.
        """
        results: List[DetectedGraphic] = []

        # 1. Check for Percentages -> Ring
        for m in self.RE_PERCENT.finditer(text):
            val = float(m.group(1))
            results.append(DetectedGraphic(
                graphic_type=GraphicType.RING,
                raw_text=m.group(0),
                numeric_value=val,
                unit="%",
                label="PERCENTAGE",
                subtitle=f"{val:.1f}% OF TOTAL",
            ))

        # 2. Check for "1 in N" -> Dot Grid
        for m in self.RE_DOT_GRID.finditer(text):
            denom_raw = m.group(1) or m.group(3)
            denom = self.WORD_NUMBERS.get(denom_raw.lower(), None)
            if denom is None:
                try:
                    denom = int(denom_raw)
                except ValueError:
                    denom = 10
            results.append(DetectedGraphic(
                graphic_type=GraphicType.DOT_GRID,
                raw_text=m.group(0),
                numeric_value=float(denom),
                unit="ratio",
                label="INCIDENCE RATIO",
                subtitle=f"1 IN {denom} PROBABILITY",
            ))

        # 3. Check for Comparisons ("N times" or "than") -> Comparison
        for m in self.RE_COMPARISON.finditer(text):
            val_str = m.group(1) or m.group(2)
            try:
                mult = float(val_str)
            except (ValueError, TypeError):
                mult = 2.0
            results.append(DetectedGraphic(
                graphic_type=GraphicType.COMPARISON,
                raw_text=m.group(0),
                numeric_value=mult,
                unit="x",
                label="MAGNITUDE RATIO",
                subtitle=f"{mult:g}x COMPARISON MULTIPLIER",
            ))

        # 4. Check for Dimensions -> Gauge
        for m in self.RE_DIMENSION.finditer(text):
            val_str = m.group(1).replace(",", "")
            unit_str = m.group(2)
            try:
                val = float(val_str)
            except ValueError:
                continue
            anchor = get_nearest_human_anchor(val, unit_str)
            results.append(DetectedGraphic(
                graphic_type=GraphicType.GAUGE,
                raw_text=m.group(0),
                numeric_value=val,
                unit=unit_str,
                label=f"{unit_str.upper()} TELEMETRY",
                subtitle=anchor.notes if (anchor and anchor.notes) else (anchor.name if anchor else ""),
                human_anchor=anchor,
            ))

        # 5. Check for 4-digit years -> Timeline
        for m in self.RE_YEAR.finditer(text):
            year_str = m.group(1) or m.group(2) or m.group(3)
            try:
                year_val = int(year_str)
            except ValueError:
                continue
            if 800 <= year_val <= 2050:
                results.append(DetectedGraphic(
                    graphic_type=GraphicType.TIMELINE,
                    raw_text=m.group(0),
                    numeric_value=float(year_val),
                    unit="AD",
                    label="HISTORICAL TIMELINE",
                    subtitle=f"EPOCH {year_val}",
                ))

        # 6. Check for Money or Large Counts -> Count-up
        for m in self.RE_MONEY.finditer(text):
            val_raw = (m.group(1) or m.group(3) or "0").replace(",", "")
            scale_word = (m.group(2) or "").lower()
            mult = 1.0
            if scale_word in ("billion", "b"):
                mult = 1e9
            elif scale_word in ("million", "m"):
                mult = 1e6
            elif scale_word in ("thousand", "k"):
                mult = 1e3
            elif scale_word == "trillion":
                mult = 1e12
            try:
                val = float(val_raw) * mult
            except ValueError:
                continue
            anchor = get_nearest_human_anchor(val, "$")
            results.append(DetectedGraphic(
                graphic_type=GraphicType.COUNTUP,
                raw_text=m.group(0),
                numeric_value=val,
                unit="$",
                label="VALUATION RECORD",
                subtitle=anchor.name if anchor else "",
                human_anchor=anchor,
            ))

        return results


# ==============================================================================
# 4. TIMING, WORD-TIMESTAMP ALIGNMENT & PACING RULES
# ==============================================================================

def align_graphics_with_narration(
    graphics: List[DetectedGraphic],
    word_timestamps: List[Dict[str, Any]],
    min_interval: float = 15.0,
    count_time: float = 1.6,
    hold_time: float = 1.0,
    fade_time: float = 0.3,
) -> List[DetectedGraphic]:
    """
    Motion & Pacing Rules:
      1. Land the count exactly as the number is spoken, using word timestamps.
      2. Hold about 1 second after.
      3. Fade in/out with ~0.3 seconds easing.
      4. Keep to roughly one graphic per 15 seconds (enforce minimum interval).
    """
    if not graphics or not word_timestamps:
        return []

    NUMBER_WORDS = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "hundred": 100, "thousand": 1000, "million": 1000000, "billion": 1000000000,
    }

    # Map spoken numeric words and word-forms to timestamp end times
    number_word_map: List[Tuple[float, float, str, float]] = []
    for w in word_timestamps:
        word = str(w.get("word", "")).strip().lower()
        start = float(w.get("start", 0.0))
        end = float(w.get("end", 0.0))
        clean_num = re.sub(r"[^\d.]", "", word.replace(",", ""))
        val = None
        if clean_num:
            try:
                val = float(clean_num)
            except ValueError:
                pass
        else:
            # Check number words / compounds (e.g. thirty-five)
            subparts = word.replace("-", " ").split()
            part_sum = 0
            for sp in subparts:
                if sp in NUMBER_WORDS:
                    part_sum += NUMBER_WORDS[sp]
            if part_sum > 0:
                val = float(part_sum)

        if val is not None or clean_num:
            number_word_map.append((start, end, word, val if val is not None else 0.0))

    aligned: List[DetectedGraphic] = []
    last_graphic_start = -999.0

    for g in graphics:
        target_land_time = None

        # 1. Search for matching number in word map
        for w_start, w_end, w_text, w_val in number_word_map:
            # Exact value match
            if w_val > 0 and abs(w_val - g.numeric_value) < 1e-2:
                target_land_time = w_end
                break
            # Scaled match (e.g. 35 spoken for 35,000,000)
            if w_val > 0 and g.numeric_value >= 1000 and (g.numeric_value % w_val == 0 or abs(g.numeric_value / w_val - 1000000) < 1e-2 or abs(g.numeric_value / w_val - 1000) < 1e-2):
                target_land_time = w_end
                break

        # 2. If not matched, search for words from raw_text or label in word_timestamps
        if target_land_time is None and g.raw_text:
            key_words = [re.sub(r"[^\w]", "", kw.lower()) for kw in g.raw_text.split() if len(kw) > 2]
            for kw in key_words:
                for w in word_timestamps:
                    clean_w = re.sub(r"[^\w]", "", str(w.get("word", "")).lower())
                    if clean_w == kw:
                        target_land_time = float(w.get("end", 0.0))
                        break
                if target_land_time:
                    break

        if target_land_time is None:
            continue

        # Enforce minimum interval pacing rule
        graphic_start = max(0.0, target_land_time - count_time)
        if (graphic_start - last_graphic_start) < min_interval:
            continue

        total_dur = count_time + hold_time + fade_time

        g.start_time = graphic_start
        g.spoken_land_time = target_land_time
        g.count_time = count_time
        g.hold_time = hold_time
        g.fade_time = fade_time
        g.duration = total_dur

        aligned.append(g)
        last_graphic_start = graphic_start

    return aligned


# ==============================================================================
# 5. MOTION MATH & PROCEDURAL RENDERING ENGINE
# ==============================================================================

def clamp(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def ease_out_cubic(x: float) -> float:
    """Ease-out for counting/progress: fast start, slow landing."""
    x = clamp(x)
    return 1.0 - (1.0 - x) ** 3


def ease_in_out(x: float) -> float:
    """Ease-in-out for fades: smooth entry and exit."""
    x = clamp(x)
    return 3.0 * x * x - 2.0 * x * x * x


def _load_best_font(size: int) -> ImageFont.ImageFont:
    if not _PIL_AVAILABLE:
        return None
    fonts_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    candidates = [
        str(fonts_dir / "Montserrat-Bold.ttf"),
        str(fonts_dir / "Inter-Bold.ttf"),
        str(fonts_dir / "Cinzel-Bold.ttf"),
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except (OSError, IOError):
            pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None



class NumberGraphicsEngine:
    """
    Deterministic rendering engine for all 6 numeric visualizer archetypes.
    Supports both transparent overlays (WebM VP9) and standalone video clips (MP4).
    Pure CPU execution, zero external dependencies beyond Pillow + FFmpeg.
    """

    SS = 2  # Supersampling factor for smooth, anti-aliased edges

    # High-contrast, broadcast aesthetic color tokens
    THEMES = {
        "panel_bg": (8, 14, 24, 210),       # Translucent slate HUD
        "solid_bg": (6, 10, 18),            # Solid dark background
        "accent_green": (0, 240, 160),      # Neon Emerald
        "accent_gold": (255, 184, 44),      # Warm Amber
        "accent_cyan": (0, 216, 255),       # Cyan telemetry
        "accent_red": (255, 68, 68),        # Urgent crimson
        "text_main": (255, 255, 255),
        "text_muted": (160, 185, 210),
        "grid_line": (20, 32, 48),
    }

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path("workspace/numgfx_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.detector = NumberGraphicDetector()

    # --------------------------------------------------------------------------
    # 1. RING (Percentages)
    # --------------------------------------------------------------------------
    def render_ring(
        self,
        percent: float,
        label: str = "PROPORTION",
        subtitle: str = "",
        dest: Optional[Path] = None,
        duration: float = 3.2,
        count_time: float = 1.6,
        fade_time: float = 0.3,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        transparent: bool = False,
    ) -> Optional[Path]:
        """Renders an animated circular percentage ring with ease-out progress."""
        if not _PIL_AVAILABLE:
            return None

        if dest is None:
            ext = "webm" if transparent else "mp4"
            key = abs(hash(f"ring_{percent}_{label}_{width}x{height}_{duration}_{transparent}"))
            dest = self.cache_dir / f"numgfx_ring_{key}.{ext}"

        if dest.exists() and dest.stat().st_size > 5000:
            return dest

        return self._render_video_pipeline(
            draw_frame_fn=lambda t: self._draw_ring_frame(t, percent, label, subtitle, duration, count_time, fade_time, width, height, transparent),
            dest=dest,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transparent=transparent,
        )

    def _draw_ring_frame(self, t, percent, label, subtitle, dur, count_time, fade, w, h, transparent):
        canvas = Image.new("RGBA", (w * self.SS, h * self.SS), (0, 0, 0, 0) if transparent else (*self.THEMES["solid_bg"], 255))
        d = ImageDraw.Draw(canvas)

        # Fade and progress
        a_in = ease_in_out(clamp(t / fade))
        a_out = ease_in_out(clamp((dur - t) / fade))
        alpha = min(a_in, a_out)

        progress = ease_out_cubic(clamp(t / count_time))
        current_pct = percent * progress

        cx, cy = (w * self.SS) // 2, (h * self.SS) // 2
        radius = int(min(w, h) * 0.28 * self.SS)
        stroke = int(28 * self.SS)

        # Outer bounding HUD box
        box_pad = radius + int(100 * self.SS)
        d.rounded_rectangle(
            [cx - box_pad, cy - box_pad, cx + box_pad, cy + box_pad],
            radius=24 * self.SS,
            fill=self.THEMES["panel_bg"] if transparent else (12, 18, 28),
            outline=self.THEMES["grid_line"],
            width=2 * self.SS,
        )

        # Background Track Circle
        d.arc([cx - radius, cy - radius, cx + radius, cy + radius],
              start=0, end=360, fill=(35, 48, 68), width=stroke)

        # Active Glowing Arc
        arc_angle = int(360.0 * (current_pct / 100.0))
        if arc_angle > 0:
            d.arc([cx - radius, cy - radius, cx + radius, cy + radius],
                  start=-90, end=-90 + arc_angle, fill=self.THEMES["accent_green"], width=stroke)

        # Center Numeric Percentage
        f_num = _load_best_font(96 * self.SS)
        f_label = _load_best_font(38 * self.SS)
        f_sub = _load_best_font(30 * self.SS)

        num_str = f"{current_pct:.0f}%" if percent.is_integer() else f"{current_pct:.1f}%"
        d.text((cx, cy - 10 * self.SS), num_str, font=f_num, fill=self.THEMES["text_main"], anchor="mm")
        d.text((cx, cy + radius + 40 * self.SS), label.upper(), font=f_label, fill=self.THEMES["accent_green"], anchor="mm")
        if subtitle:
            d.text((cx, cy + radius + 85 * self.SS), subtitle.upper(), font=f_sub, fill=self.THEMES["text_muted"], anchor="mm")

        # Global opacity
        if alpha < 1.0:
            r, g, b, a = canvas.split()
            a = a.point(lambda p: int(p * alpha))
            canvas = Image.merge("RGBA", (r, g, b, a))

        return canvas.resize((w, h), Image.LANCZOS)

    # --------------------------------------------------------------------------
    # 2. TIMELINE (Four-Digit Years)
    # --------------------------------------------------------------------------
    def render_timeline(
        self,
        target_year: int,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        label: str = "HISTORICAL ANCHOR",
        subtitle: str = "",
        dest: Optional[Path] = None,
        duration: float = 3.2,
        count_time: float = 1.6,
        fade_time: float = 0.3,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        transparent: bool = False,
    ) -> Optional[Path]:
        """Renders an era timeline with an animated cursor landing on the exact year."""
        if not _PIL_AVAILABLE:
            return None

        if dest is None:
            ext = "webm" if transparent else "mp4"
            key = abs(hash(f"timeline_{target_year}_{label}_{width}x{height}_{duration}_{transparent}"))
            dest = self.cache_dir / f"numgfx_timeline_{key}.{ext}"

        if dest.exists() and dest.stat().st_size > 5000:
            return dest

        s_yr = start_year or (target_year - 200)
        e_yr = end_year or (target_year + 100)

        return self._render_video_pipeline(
            draw_frame_fn=lambda t: self._draw_timeline_frame(t, target_year, s_yr, e_yr, label, subtitle, duration, count_time, fade_time, width, height, transparent),
            dest=dest,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transparent=transparent,
        )

    def _draw_timeline_frame(self, t, target_yr, start_yr, end_yr, label, subtitle, dur, count_time, fade, w, h, transparent):
        canvas = Image.new("RGBA", (w * self.SS, h * self.SS), (0, 0, 0, 0) if transparent else (*self.THEMES["solid_bg"], 255))
        d = ImageDraw.Draw(canvas)

        a_in = ease_in_out(clamp(t / fade))
        a_out = ease_in_out(clamp((dur - t) / fade))
        alpha = min(a_in, a_out)

        progress = ease_out_cubic(clamp(t / count_time))
        current_display_yr = int(start_yr + (target_yr - start_yr) * progress)

        cx, cy = (w * self.SS) // 2, (h * self.SS) // 2
        card_w, card_h = int(w * 0.88 * self.SS), int(360 * self.SS)
        x0, y0 = cx - card_w // 2, cy - card_h // 2

        # Card container
        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=24 * self.SS,
                            fill=self.THEMES["panel_bg"] if transparent else (12, 18, 28),
                            outline=self.THEMES["grid_line"], width=2 * self.SS)

        # Header tag
        f_badge = _load_best_font(32 * self.SS)
        f_big = _load_best_font(110 * self.SS)
        f_sub = _load_best_font(34 * self.SS)

        d.text((x0 + 40 * self.SS, y0 + 40 * self.SS), f"●  {label.upper()}", font=f_badge, fill=self.THEMES["accent_gold"])

        # Giant counting year
        d.text((cx, y0 + 130 * self.SS), str(current_display_yr), font=f_big, fill=self.THEMES["text_main"], anchor="mm")

        # Timeline track axis
        track_y = y0 + 240 * self.SS
        track_x0, track_x1 = x0 + 60 * self.SS, x0 + card_w - 60 * self.SS
        d.line([(track_x0, track_y), (track_x1, track_y)], fill=(40, 56, 78), width=6 * self.SS)

        # Year pointer landing
        target_norm = (target_yr - start_yr) / max(1, end_yr - start_yr)
        cursor_x = int(track_x0 + (track_x1 - track_x0) * (target_norm * progress))

        # Filled progress track
        d.line([(track_x0, track_y), (cursor_x, track_y)], fill=self.THEMES["accent_gold"], width=6 * self.SS)
        # Ping beacon circle
        d.ellipse([cursor_x - 14 * self.SS, track_y - 14 * self.SS, cursor_x + 14 * self.SS, track_y + 14 * self.SS],
                  fill=self.THEMES["accent_gold"], outline=(255, 255, 255), width=2 * self.SS)

        if subtitle:
            d.text((cx, y0 + 300 * self.SS), subtitle.upper(), font=f_sub, fill=self.THEMES["text_muted"], anchor="mm")

        if alpha < 1.0:
            r, g, b, a = canvas.split()
            a = a.point(lambda p: int(p * alpha))
            canvas = Image.merge("RGBA", (r, g, b, a))

        return canvas.resize((w, h), Image.LANCZOS)

    # --------------------------------------------------------------------------
    # 3. GAUGE (Length, Depth, Height Units with Human Anchor)
    # --------------------------------------------------------------------------
    def render_gauge(
        self,
        value: float,
        unit: str,
        label: str = "DEPTH MEASUREMENT",
        human_anchor: Optional[HumanAnchor] = None,
        dest: Optional[Path] = None,
        duration: float = 3.2,
        count_time: float = 1.6,
        fade_time: float = 0.3,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        transparent: bool = False,
    ) -> Optional[Path]:
        """Renders a vertical altitude/depth measuring gauge with verified scale comparison."""
        if not _PIL_AVAILABLE:
            return None

        if dest is None:
            ext = "webm" if transparent else "mp4"
            key = abs(hash(f"gauge_{value}_{unit}_{label}_{width}x{height}_{duration}_{transparent}"))
            dest = self.cache_dir / f"numgfx_gauge_{key}.{ext}"

        if dest.exists() and dest.stat().st_size > 5000:
            return dest

        anchor = human_anchor or get_nearest_human_anchor(value, unit)

        return self._render_video_pipeline(
            draw_frame_fn=lambda t: self._draw_gauge_frame(t, value, unit, label, anchor, duration, count_time, fade_time, width, height, transparent),
            dest=dest,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transparent=transparent,
        )

    def _draw_gauge_frame(self, t, value, unit, label, anchor, dur, count_time, fade, w, h, transparent):
        canvas = Image.new("RGBA", (w * self.SS, h * self.SS), (0, 0, 0, 0) if transparent else (*self.THEMES["solid_bg"], 255))
        d = ImageDraw.Draw(canvas)

        a_in = ease_in_out(clamp(t / fade))
        a_out = ease_in_out(clamp((dur - t) / fade))
        alpha = min(a_in, a_out)

        progress = ease_out_cubic(clamp(t / count_time))
        current_val = value * progress

        cx, cy = (w * self.SS) // 2, (h * self.SS) // 2
        card_w, card_h = int(w * 0.88 * self.SS), int(480 * self.SS)
        x0, y0 = cx - card_w // 2, cy - card_h // 2

        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=24 * self.SS,
                            fill=self.THEMES["panel_bg"] if transparent else (12, 18, 28),
                            outline=self.THEMES["grid_line"], width=2 * self.SS)

        f_badge = _load_best_font(32 * self.SS)
        f_num = _load_best_font(90 * self.SS)
        f_unit = _load_best_font(44 * self.SS)
        f_anchor = _load_best_font(28 * self.SS)

        # Header tag
        d.text((x0 + 40 * self.SS, y0 + 40 * self.SS), f"●  {label.upper()}", font=f_badge, fill=self.THEMES["accent_cyan"])

        # Gauge track on the left
        gauge_x = x0 + 70 * self.SS
        gauge_y0 = y0 + 100 * self.SS
        gauge_h = int(240 * self.SS)
        gauge_y1 = gauge_y0 + gauge_h

        # Rail bar
        d.rounded_rectangle([gauge_x, gauge_y0, gauge_x + 24 * self.SS, gauge_y1], radius=12 * self.SS, fill=(30, 45, 65))
        fill_h = int(gauge_h * progress)
        d.rounded_rectangle([gauge_x, gauge_y1 - fill_h, gauge_x + 24 * self.SS, gauge_y1], radius=12 * self.SS, fill=self.THEMES["accent_cyan"])

        # Tick marks along gauge
        for step in range(5):
            ty = gauge_y0 + (gauge_h * step) // 4
            d.line([(gauge_x + 32 * self.SS, ty), (gauge_x + 48 * self.SS, ty)], fill=(80, 110, 145), width=3 * self.SS)

        # Number and unit on the right
        num_str = f"{int(current_val):,}" if value >= 10 else f"{current_val:.1f}"
        d.text((x0 + 130 * self.SS, y0 + 120 * self.SS), num_str, font=f_num, fill=self.THEMES["text_main"])
        d.text((x0 + 130 * self.SS, y0 + 220 * self.SS), unit.upper(), font=f_unit, fill=self.THEMES["accent_cyan"])

        # Hand-checked human anchor comparison
        if anchor:
            anchor_box_y = y0 + 360 * self.SS
            d.rounded_rectangle([x0 + 40 * self.SS, anchor_box_y, x0 + card_w - 40 * self.SS, anchor_box_y + 80 * self.SS],
                                radius=12 * self.SS, fill=(16, 26, 42), outline=(32, 50, 75), width=1 * self.SS)
            ratio = value / max(1e-9, normalize_to_meters(anchor.value, anchor.unit) if unit.lower() in ("m", "meter", "ft", "feet", "km") else anchor.value)
            d.text((x0 + 60 * self.SS, anchor_box_y + 20 * self.SS),
                   f"SCALE: {ratio:.1f}x {anchor.name.upper()}", font=f_anchor, fill=self.THEMES["accent_gold"])
            d.text((x0 + 60 * self.SS, anchor_box_y + 48 * self.SS),
                   f"SOURCED REF: {anchor.source}", font=_load_best_font(22 * self.SS), fill=self.THEMES["text_muted"])

        if alpha < 1.0:
            r, g, b, a = canvas.split()
            a = a.point(lambda p: int(p * alpha))
            canvas = Image.merge("RGBA", (r, g, b, a))

        return canvas.resize((w, h), Image.LANCZOS)

    # --------------------------------------------------------------------------
    # 4. COUNT-UP (Money or Large Counts)
    # --------------------------------------------------------------------------
    def render_countup(
        self,
        value: float,
        unit: str = "",
        label: str = "OFFICIAL RECORD",
        subtitle: str = "",
        dest: Optional[Path] = None,
        duration: float = 3.2,
        count_time: float = 1.6,
        fade_time: float = 0.3,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        transparent: bool = False,
    ) -> Optional[Path]:
        """Renders an eased count-up HUD panel for money, counts, and stats."""
        if not _PIL_AVAILABLE:
            return None

        if dest is None:
            ext = "webm" if transparent else "mp4"
            key = abs(hash(f"countup_{value}_{unit}_{label}_{width}x{height}_{duration}_{transparent}"))
            dest = self.cache_dir / f"numgfx_countup_{key}.{ext}"

        if dest.exists() and dest.stat().st_size > 5000:
            return dest

        return self._render_video_pipeline(
            draw_frame_fn=lambda t: self._draw_countup_frame(t, value, unit, label, subtitle, duration, count_time, fade_time, width, height, transparent),
            dest=dest,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transparent=transparent,
        )

    def _draw_countup_frame(self, t, value, unit, label, subtitle, dur, count_time, fade, w, h, transparent):
        canvas = Image.new("RGBA", (w * self.SS, h * self.SS), (0, 0, 0, 0) if transparent else (*self.THEMES["solid_bg"], 255))
        d = ImageDraw.Draw(canvas)

        a_in = ease_in_out(clamp(t / fade))
        a_out = ease_in_out(clamp((dur - t) / fade))
        alpha = min(a_in, a_out)

        progress = ease_out_cubic(clamp(t / count_time))
        current_num = int(round(value * progress))

        cx, cy = (w * self.SS) // 2, (h * self.SS) // 2
        card_w, card_h = int(w * 0.88 * self.SS), int(340 * self.SS)
        x0, y0 = cx - card_w // 2, cy - card_h // 2

        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=24 * self.SS,
                            fill=self.THEMES["panel_bg"] if transparent else (12, 18, 28),
                            outline=self.THEMES["grid_line"], width=2 * self.SS)

        f_num = _load_best_font(100 * self.SS)
        f_unit = _load_best_font(46 * self.SS)
        f_label = _load_best_font(34 * self.SS)

        # Number + Unit string
        num_str = f"{current_num:,}"
        if unit in ("$", "£", "€"):
            disp_str = f"{unit}{num_str}"
        elif unit:
            disp_str = f"{num_str} {unit.upper()}"
        else:
            disp_str = num_str

        d.text((cx, y0 + 100 * self.SS), disp_str, font=f_num, fill=self.THEMES["text_main"], anchor="mm")

        # Accent bar
        bar_y = y0 + 200 * self.SS
        bar_w = card_w - 120 * self.SS
        d.rounded_rectangle([cx - bar_w // 2, bar_y, cx - bar_w // 2 + int(bar_w * progress), bar_y + 10 * self.SS],
                            radius=5 * self.SS, fill=self.THEMES["accent_gold"])

        # Label
        d.text((cx, y0 + 250 * self.SS), label.upper(), font=f_label, fill=self.THEMES["text_muted"], anchor="mm")

        if alpha < 1.0:
            r, g, b, a = canvas.split()
            a = a.point(lambda p: int(p * alpha))
            canvas = Image.merge("RGBA", (r, g, b, a))

        return canvas.resize((w, h), Image.LANCZOS)

    # --------------------------------------------------------------------------
    # 5. COMPARISON ("N times" or "than")
    # --------------------------------------------------------------------------
    def render_comparison(
        self,
        multiplier: float,
        baseline_name: str = "BASELINE",
        target_name: str = "NEW RECORD",
        label: str = "RELATIVE SCALE COMPARISON",
        dest: Optional[Path] = None,
        duration: float = 3.2,
        count_time: float = 1.6,
        fade_time: float = 0.3,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        transparent: bool = False,
    ) -> Optional[Path]:
        """Renders dual comparative bars contrasting baseline vs target with multiplier badge."""
        if not _PIL_AVAILABLE:
            return None

        if dest is None:
            ext = "webm" if transparent else "mp4"
            key = abs(hash(f"comp_{multiplier}_{baseline_name}_{width}x{height}_{duration}_{transparent}"))
            dest = self.cache_dir / f"numgfx_comp_{key}.{ext}"

        if dest.exists() and dest.stat().st_size > 5000:
            return dest

        return self._render_video_pipeline(
            draw_frame_fn=lambda t: self._draw_comparison_frame(t, multiplier, baseline_name, target_name, label, duration, count_time, fade_time, width, height, transparent),
            dest=dest,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transparent=transparent,
        )

    def _draw_comparison_frame(self, t, mult, base_name, target_name, label, dur, count_time, fade, w, h, transparent):
        canvas = Image.new("RGBA", (w * self.SS, h * self.SS), (0, 0, 0, 0) if transparent else (*self.THEMES["solid_bg"], 255))
        d = ImageDraw.Draw(canvas)

        a_in = ease_in_out(clamp(t / fade))
        a_out = ease_in_out(clamp((dur - t) / fade))
        alpha = min(a_in, a_out)

        progress = ease_out_cubic(clamp(t / count_time))
        current_mult = 1.0 + (mult - 1.0) * progress

        cx, cy = (w * self.SS) // 2, (h * self.SS) // 2
        card_w, card_h = int(w * 0.88 * self.SS), int(420 * self.SS)
        x0, y0 = cx - card_w // 2, cy - card_h // 2

        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=24 * self.SS,
                            fill=self.THEMES["panel_bg"] if transparent else (12, 18, 28),
                            outline=self.THEMES["grid_line"], width=2 * self.SS)

        f_badge = _load_best_font(32 * self.SS)
        f_mult = _load_best_font(84 * self.SS)
        f_bar = _load_best_font(30 * self.SS)

        d.text((x0 + 40 * self.SS, y0 + 40 * self.SS), f"●  {label.upper()}", font=f_badge, fill=self.THEMES["accent_green"])

        # Multiplier Badge
        mult_str = f"{current_mult:.1f}x" if mult != int(mult) else f"{int(current_mult)}x"
        d.text((cx, y0 + 120 * self.SS), f"{mult_str} GREATER", font=f_mult, fill=self.THEMES["accent_green"], anchor="mm")

        # Bar 1: Baseline
        bar_max_w = card_w - 200 * self.SS
        bar1_w = int(bar_max_w / max(1.5, mult))
        b1_y = y0 + 220 * self.SS
        d.rounded_rectangle([x0 + 50 * self.SS, b1_y, x0 + 50 * self.SS + bar1_w, b1_y + 36 * self.SS],
                            radius=8 * self.SS, fill=(40, 56, 78))
        d.text((x0 + 60 * self.SS, b1_y + 8 * self.SS), f"1.0x  {base_name.upper()}", font=f_bar, fill=self.THEMES["text_muted"])

        # Bar 2: Target
        b2_y = y0 + 290 * self.SS
        bar2_w = int(bar1_w + (bar_max_w - bar1_w) * progress)
        d.rounded_rectangle([x0 + 50 * self.SS, b2_y, x0 + 50 * self.SS + bar2_w, b2_y + 36 * self.SS],
                            radius=8 * self.SS, fill=self.THEMES["accent_green"])
        d.text((x0 + 60 * self.SS, b2_y + 8 * self.SS), f"{mult_str}  {target_name.upper()}", font=f_bar, fill=(10, 20, 30))

        if alpha < 1.0:
            r, g, b, a = canvas.split()
            a = a.point(lambda p: int(p * alpha))
            canvas = Image.merge("RGBA", (r, g, b, a))

        return canvas.resize((w, h), Image.LANCZOS)

    # --------------------------------------------------------------------------
    # 6. DOT GRID ("1 in N")
    # --------------------------------------------------------------------------
    def render_dot_grid(
        self,
        ratio_n: int,
        label: str = "INCIDENCE FREQUENCY",
        subtitle: str = "",
        dest: Optional[Path] = None,
        duration: float = 3.2,
        count_time: float = 1.6,
        fade_time: float = 0.3,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        transparent: bool = False,
    ) -> Optional[Path]:
        """Renders a visual dot grid matrix highlighting 1 in N occurrences."""
        if not _PIL_AVAILABLE:
            return None

        if dest is None:
            ext = "webm" if transparent else "mp4"
            key = abs(hash(f"dotgrid_{ratio_n}_{label}_{width}x{height}_{duration}_{transparent}"))
            dest = self.cache_dir / f"numgfx_dotgrid_{key}.{ext}"

        if dest.exists() and dest.stat().st_size > 5000:
            return dest

        return self._render_video_pipeline(
            draw_frame_fn=lambda t: self._draw_dot_grid_frame(t, ratio_n, label, subtitle, duration, count_time, fade_time, width, height, transparent),
            dest=dest,
            duration=duration,
            fps=fps,
            width=width,
            height=height,
            transparent=transparent,
        )

    def _draw_dot_grid_frame(self, t, n, label, subtitle, dur, count_time, fade, w, h, transparent):
        canvas = Image.new("RGBA", (w * self.SS, h * self.SS), (0, 0, 0, 0) if transparent else (*self.THEMES["solid_bg"], 255))
        d = ImageDraw.Draw(canvas)

        a_in = ease_in_out(clamp(t / fade))
        a_out = ease_in_out(clamp((dur - t) / fade))
        alpha = min(a_in, a_out)

        progress = ease_out_cubic(clamp(t / count_time))

        cx, cy = (w * self.SS) // 2, (h * self.SS) // 2
        card_w, card_h = int(w * 0.88 * self.SS), int(460 * self.SS)
        x0, y0 = cx - card_w // 2, cy - card_h // 2

        d.rounded_rectangle([x0, y0, x0 + card_w, y0 + card_h], radius=24 * self.SS,
                            fill=self.THEMES["panel_bg"] if transparent else (12, 18, 28),
                            outline=self.THEMES["grid_line"], width=2 * self.SS)

        f_badge = _load_best_font(32 * self.SS)
        f_num = _load_best_font(76 * self.SS)
        f_sub = _load_best_font(32 * self.SS)

        d.text((x0 + 40 * self.SS, y0 + 40 * self.SS), f"●  {label.upper()}", font=f_badge, fill=self.THEMES["accent_red"])
        d.text((cx, y0 + 110 * self.SS), f"1 IN {n}", font=f_num, fill=self.THEMES["text_main"], anchor="mm")

        # Determine grid size (display 10 to 50 dots)
        total_dots = min(50, max(10, n))
        cols = 10
        rows = math.ceil(total_dots / cols)

        grid_w = cols * 44 * self.SS
        gx0 = cx - grid_w // 2
        gy0 = y0 + 190 * self.SS
        dot_r = 14 * self.SS

        for idx in range(total_dots):
            row_idx = idx // cols
            col_idx = idx % cols
            dot_cx = gx0 + col_idx * 44 * self.SS + 20 * self.SS
            dot_cy = gy0 + row_idx * 44 * self.SS + 20 * self.SS

            if idx == 0:
                # The 1 highlighted dot (pulsing with progress)
                pulse_r = int(dot_r * (1.0 + 0.3 * (1.0 - progress)))
                d.ellipse([dot_cx - pulse_r, dot_cy - pulse_r, dot_cx + pulse_r, dot_cy + pulse_r],
                          fill=self.THEMES["accent_red"], outline=(255, 255, 255), width=2 * self.SS)
            else:
                # Neutral background dots
                d.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r],
                          fill=(35, 48, 68))

        if subtitle:
            d.text((cx, y0 + card_h - 45 * self.SS), subtitle.upper(), font=f_sub, fill=self.THEMES["text_muted"], anchor="mm")

        if alpha < 1.0:
            r, g, b, a = canvas.split()
            a = a.point(lambda p: int(p * alpha))
            canvas = Image.merge("RGBA", (r, g, b, a))

        return canvas.resize((w, h), Image.LANCZOS)

    # --------------------------------------------------------------------------
    # PIPELINE DISPATCH & ENCODING
    # --------------------------------------------------------------------------
    def render_graphic(
        self,
        graphic: DetectedGraphic,
        dest: Optional[Path] = None,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        transparent: bool = False,
    ) -> Optional[Path]:
        """Dispatches a DetectedGraphic to its designated archetype renderer."""
        gt = graphic.graphic_type
        dur = graphic.duration
        cnt = graphic.count_time
        fade = graphic.fade_time

        if gt == GraphicType.RING:
            return self.render_ring(
                percent=graphic.numeric_value,
                label=graphic.label or "PROPORTION",
                subtitle=graphic.subtitle,
                dest=dest, duration=dur, count_time=cnt, fade_time=fade,
                width=width, height=height, fps=fps, transparent=transparent,
            )
        elif gt == GraphicType.TIMELINE:
            return self.render_timeline(
                target_year=int(graphic.numeric_value),
                label=graphic.label or "HISTORICAL EPOCH",
                subtitle=graphic.subtitle,
                dest=dest, duration=dur, count_time=cnt, fade_time=fade,
                width=width, height=height, fps=fps, transparent=transparent,
            )
        elif gt == GraphicType.GAUGE:
            return self.render_gauge(
                value=graphic.numeric_value,
                unit=graphic.unit,
                label=graphic.label or "DIMENSION GAUGE",
                human_anchor=graphic.human_anchor,
                dest=dest, duration=dur, count_time=cnt, fade_time=fade,
                width=width, height=height, fps=fps, transparent=transparent,
            )
        elif gt == GraphicType.COMPARISON:
            return self.render_comparison(
                multiplier=graphic.numeric_value,
                label=graphic.label or "MAGNITUDE COMPARISON",
                dest=dest, duration=dur, count_time=cnt, fade_time=fade,
                width=width, height=height, fps=fps, transparent=transparent,
            )
        elif gt == GraphicType.DOT_GRID:
            return self.render_dot_grid(
                ratio_n=int(graphic.numeric_value),
                label=graphic.label or "INCIDENCE PROBABILITY",
                subtitle=graphic.subtitle,
                dest=dest, duration=dur, count_time=cnt, fade_time=fade,
                width=width, height=height, fps=fps, transparent=transparent,
            )
        else:  # COUNTUP default
            return self.render_countup(
                value=graphic.numeric_value,
                unit=graphic.unit,
                label=graphic.label or "OFFICIAL STAT",
                subtitle=graphic.subtitle,
                dest=dest, duration=dur, count_time=cnt, fade_time=fade,
                width=width, height=height, fps=fps, transparent=transparent,
            )

    def render_counter(
        self,
        final_value: str,
        label: str = "",
        dest: Optional[Path] = None,
        duration: float = 3.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        **kwargs,
    ) -> Optional[Path]:
        """Backwards-compatible wrapper for render_countup."""
        digits = re.sub(r"[^\d.]", "", str(final_value).replace(",", ""))
        try:
            val = float(digits)
        except ValueError:
            val = 0.0
        suffix = re.sub(r"[\d.,]", "", str(final_value)).strip()
        return self.render_countup(
            value=val,
            unit=suffix,
            label=label or "TELEMETRY",
            dest=dest,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            transparent=False,
        )

    def render_stat_card(
        self,
        stats: list[tuple[str, str]],
        dest: Optional[Path] = None,
        duration: float = 3.0,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
        **kwargs,
    ) -> Optional[Path]:
        """Backwards-compatible wrapper for multi-stat card rendering."""
        if not stats:
            return None
        val_str, label = stats[0]
        digits = re.sub(r"[^\d.]", "", str(val_str).replace(",", ""))
        try:
            val = float(digits)
        except ValueError:
            val = 0.0
        suffix = re.sub(r"[\d.,]", "", str(val_str)).strip()
        sub = " | ".join(f"{v}: {l}" for v, l in stats[1:]) if len(stats) > 1 else ""
        return self.render_countup(
            value=val,
            unit=suffix,
            label=label,
            subtitle=sub,
            dest=dest,
            duration=duration,
            width=width,
            height=height,
            fps=fps,
            transparent=False,
        )

    def _render_video_pipeline(
        self,
        draw_frame_fn,
        dest: Path,
        duration: float,
        fps: int,
        width: int,
        height: int,
        transparent: bool,
    ) -> Optional[Path]:
        """Encodes frames to either transparent WebM (VP9 yuva420p) or standard MP4 (libx264) via direct rawvideo pipe."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        n_frames = int(round(duration * fps))

        if transparent:
            # WebM VP9 with alpha channel
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "rgba",
                "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-auto-alt-ref", "0",
                "-b:v", "0",
                "-crf", "26",
                str(dest),
            ]
        else:
            # Standard MP4
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "rgba",
                "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                str(dest),
            ]

        try:
            proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
            for i in range(n_frames):
                t = i / fps
                frame_img = draw_frame_fn(t)
                proc.stdin.write(frame_img.tobytes())
            proc.stdin.close()
            if proc.wait() != 0:
                print(f"[NumberGraphics] FFmpeg rawvideo pipe failed")
                return None
        except Exception as e:
            print(f"[NumberGraphics] Error rendering video pipe: {e}")
            return None

        return dest
