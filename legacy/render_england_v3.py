"""
render_england_v3.py — England Documentary Remaster v3
=======================================================
Architecture: 100% FFmpeg-native (no PIL frame loops).
Fix for freeze: each scene uses -stream_loop -1 + FFmpeg vf for
Ken Burns, color grade, and overlay. PIL only draws static overlay
PNGs which are then composited with overlay= filter.
Voice: en-US-ChristopherNeural (authoritative, deep)
Subtitles: ASS burn in final pass (Impact font, neon green Hormozi)
Variable Designs: each of 15 scenes gets a unique visual design template.
"""

import asyncio
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────────────────────
#  PATHS
# ─────────────────────────────────────────────────────────────
PROJECT = Path(__file__).parent
RUN_DIR = PROJECT / "workspace/runs/history_of_england_v3"
ASSETS  = PROJECT / "workspace/runs/history_of_england_remastered/curated_assets"
MUSIC   = PROJECT / "assets/music/ambient_drone.mp3"
TIMINGS = PROJECT / "workspace/runs/history_of_england_remastered/02_scene_timings.json"
OLD_RUN = PROJECT / "workspace/runs/history_of_england_under_60s"
TEMP    = RUN_DIR / "temp"

W, H, FPS = 1080, 1920, 30

# ─────────────────────────────────────────────────────────────
#  VOICE
# ─────────────────────────────────────────────────────────────
VOICE = "en-US-ChristopherNeural"   # deep authoritative American narrator
RATE  = "+25%"

# ─────────────────────────────────────────────────────────────
#  NARRATION SCRIPT  (identical to v2 — same proven script)
# ─────────────────────────────────────────────────────────────
SCRIPT = """How did this tiny island conquer twenty-four percent of Earth?
Two thousand years ago, Roman legions seized Britannia.
Then Norse raiders baptised it in blood.
In 1066, one battle changed everything.
The Normans forged England's law, language, and spine.
The Magna Carta stripped kings of absolute power — forever.
Tudor warships patrolled every ocean.
Then steam rewrote history.
England became the workshop of the world.
Thirty-five million square kilometres — the largest empire ever seen.
Four hundred million people under one crown.
Two world wars shattered that empire.
But England's language, law, and culture never left.
Today two billion people speak its tongue.
Like and subscribe to uncover the unsealed files."""

# ─────────────────────────────────────────────────────────────
#  SCENE TABLE  —  one row per scene
#  design: see DESIGN_MAP below
# ─────────────────────────────────────────────────────────────
SCENES = [
    # id         asset                        motion       design
    ("act1_s1", "british_empire_map.jpg",    "zoom_in",   "HOOK_MAP"),
    ("act1_s2", "roman_legions.mp4",         "pan_right", "ROMAN_DOSSIER"),
    ("act1_s3", "viking_ship.mp4",           "zoom_out",  "DARK_NORSE"),
    ("act2_s1", "bayeux_tapestry_harold.jpg","crash_zoom","BATTLE_BREAKING"),
    ("act2_s2", "domesday_book.png",         "pan_left",  "ARCHIVAL_DOC"),
    ("act2_s3", "magna_carta.jpg",           "zoom_in",   "LAW_SEAL"),
    ("act3_s1", "tudor_navy.mp4",            "pan_right", "NAVY_HUD"),
    ("act3_s2", "steam_engine.mp4",          "zoom_in",   "INDUSTRIAL_ORANGE"),
    ("act4_s1", "foundry_workshop.mp4",      "pan_left",  "FACTORY_TITLE"),
    ("act4_s2", "british_empire_map.jpg",    "pan_right", "COUNTUP_GLOBE"),   # 35M km²
    ("act4_s3", "british_empire_map.jpg",    "zoom_out",  "SUBJECTS_COUNT"),  # 400M
    ("act5_s1", "london_blitz_1940.jpg",     "zoom_in",   "WAR_BW"),
    ("act5_s2", "ve_day_crowd.mp4",          "pan_right", "VE_DAY_GOLD"),
    ("act6_s1", "westminster_aerial.mp4",    "zoom_out",  "LEGACY_PURPLE"),
    ("act6_s2", "big_ben_tower.mp4",         "zoom_in",   "CTA_SUBSCRIBE"),
]

# ─────────────────────────────────────────────────────────────
#  FONT SETUP
# ─────────────────────────────────────────────────────────────
FONT_DIR = Path("C:/Windows/Fonts")

def _font(name, size):
    candidates = [name, "impact.ttf", "arial.ttf", "arialbd.ttf"]
    for c in candidates:
        p = FONT_DIR / c
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()

# ─────────────────────────────────────────────────────────────
#  OVERLAY IMAGE BUILDERS  (PIL → PNG → FFmpeg overlay filter)
# ─────────────────────────────────────────────────────────────

def _stamp_text(img, text, x, y, fnt, color=(255,255,255), outline=(0,0,0), align="left"):
    d = ImageDraw.Draw(img)
    for dx in (-3,0,3):
        for dy in (-3,0,3):
            d.text((x+dx, y+dy), text, font=fnt, fill=outline)
    d.text((x, y), text, font=fnt, fill=color)

def _rounded_rect(img, x1, y1, x2, y2, r, color):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x1,y1,x2,y2], radius=r, fill=color)

def make_overlay_hook_map(path: Path):
    """Red 24% badge + empire label — cinematic dark vignette overlay"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    # Top vignette bar
    bar = Image.new("RGBA", (W, 280), (0,0,0,180))
    img.paste(bar, (0,0), bar)
    # 24% badge
    _rounded_rect(img, 60, 80, 480, 220, 18, (220,30,30,240))
    fnt_lg = _font("impact.ttf", 110)
    fnt_sm = _font("impact.ttf", 42)
    _stamp_text(img, "24%", 90, 82, fnt_lg, color=(255,255,80), outline=(0,0,0))
    _stamp_text(img, "OF EARTH'S LAND", 90, 205, fnt_sm, color=(255,255,255), outline=(0,0,0))
    # Bottom label
    _rounded_rect(img, 0, H-180, W, H, 0, (0,0,0,160))
    fnt_title = _font("impact.ttf", 52)
    _stamp_text(img, "BRITISH EMPIRE — PEAK 1920", 40, H-160, fnt_title, color=(255,220,100), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_roman_dossier(path: Path):
    """Classified dossier style — red BRITANNIA stamp, year badge"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    # Sepia vignette strip top
    _rounded_rect(img, 0, 0, W, 90, 0, (40,25,10,200))
    fnt_sm = _font("impact.ttf", 44)
    fnt_lg = _font("impact.ttf", 96)
    # Classified stamp (rotated — draw on temp then paste)
    stamp = Image.new("RGBA", (600, 120), (0,0,0,0))
    _rounded_rect(stamp, 0, 0, 600, 120, 12, (200,20,20,210))
    d2 = ImageDraw.Draw(stamp)
    d2.text((20, 10), "CLASSIFIED: BRITANNIA", font=fnt_sm, fill=(255,255,200))
    stamp = stamp.rotate(8, expand=True)
    img.paste(stamp, (60, 120), stamp)
    # Year HUD
    _rounded_rect(img, 60, 1650, 400, 1780, 14, (20,20,20,220))
    _stamp_text(img, "43 AD", 80, 1652, fnt_lg, color=(255,200,80), outline=(0,0,0))
    _stamp_text(img, "ROMAN INVASION", 80, 1760, fnt_sm, color=(200,180,140), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_dark_norse(path: Path):
    """Cold blue / Norse geometric border top and bottom"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 46)
    fnt_title = _font("impact.ttf", 68)
    # Top geometric stripe
    _rounded_rect(img, 0, 0, W, 12, 0, (80,140,220,255))
    _rounded_rect(img, 0, 18, W, 22, 0, (80,140,220,200))
    # Year
    _rounded_rect(img, 0, 0, W, 110, 0, (0,10,40,200))
    _stamp_text(img, "793 AD — LINDISFARNE RAID", 40, 18, fnt_sm, color=(140,200,255), outline=(0,0,0))
    # Bottom threat label
    _rounded_rect(img, 0, H-130, W, H, 0, (0,10,40,220))
    _rounded_rect(img, 0, H-130, W, H-126, 0, (80,140,220,255))
    _stamp_text(img, "NORSE RAIDERS — BAPTISED IN BLOOD", 30, H-118, fnt_sm, color=(200,230,255), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_battle_breaking(path: Path):
    """Breaking news style — red BREAKING banner, 1066 date"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_break = _font("impact.ttf", 56)
    fnt_title = _font("impact.ttf", 88)
    fnt_sm = _font("impact.ttf", 42)
    # Red breaking banner at top
    _rounded_rect(img, 0, 0, W, 130, 0, (200,20,20,240))
    _stamp_text(img, "BREAKING HISTORY", 40, 18, fnt_break, color=(255,255,80), outline=(0,0,0))
    _stamp_text(img, "1066", 40, 78, fnt_break, color=(255,255,255), outline=(0,0,0))
    # Bottom label
    _rounded_rect(img, 0, H-200, W, H, 0, (0,0,0,200))
    _stamp_text(img, "BATTLE OF HASTINGS", 40, H-185, fnt_title, color=(255,220,100), outline=(0,0,0))
    _stamp_text(img, "ONE BATTLE CHANGED EVERYTHING", 40, H-100, fnt_sm, color=(220,220,220), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_archival_doc(path: Path):
    """Old parchment document frame — Domesday Book aesthetic"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 44)
    fnt_title = _font("impact.ttf", 72)
    # Aged paper overlay top strip
    _rounded_rect(img, 0, 0, W, 80, 0, (80,60,20,200))
    _stamp_text(img, "DOMESDAY BOOK  |  1086 AD", 30, 14, fnt_sm, color=(220,190,130), outline=(0,0,0))
    # Corner document border
    d = ImageDraw.Draw(img)
    for t in range(4):
        d.rectangle([20+t, 100+t, W-20-t, H-100-t], outline=(160,120,60,140))
    # Bottom legend
    _rounded_rect(img, 0, H-160, W, H, 0, (50,35,10,220))
    _stamp_text(img, "ENGLAND'S FIRST CENSUS", 40, H-150, fnt_title, color=(230,200,140), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_law_seal(path: Path):
    """Legal document look — Magna Carta seal stamp"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 44)
    fnt_title = _font("impact.ttf", 72)
    fnt_year = _font("impact.ttf", 96)
    # Top bar
    _rounded_rect(img, 0, 0, W, 100, 0, (20,20,60,220))
    _stamp_text(img, "ROYAL DECREE — SEALED 1215", 30, 14, fnt_sm, color=(180,180,255), outline=(0,0,0))
    # Wax seal circle (bottom right)
    d = ImageDraw.Draw(img)
    cx, cy, r = 850, 1700, 140
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(180,20,20,220), outline=(220,160,80,255), width=6)
    fnt_seal = _font("impact.ttf", 40)
    _stamp_text(img, "MAGNA", cx-65, cy-55, fnt_seal, color=(255,220,120), outline=(0,0,0))
    _stamp_text(img, "CARTA", cx-60, cy+5, fnt_seal, color=(255,220,120), outline=(0,0,0))
    # Bottom
    _rounded_rect(img, 0, H-160, W, H, 0, (0,0,0,210))
    _stamp_text(img, "KINGS STRIPPED OF POWER — FOREVER", 30, H-150, fnt_title, color=(200,200,255), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_navy_hud(path: Path):
    """Tactical naval HUD — coordinates, fleet intel"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 40)
    fnt_title = _font("impact.ttf", 64)
    d = ImageDraw.Draw(img)
    # HUD corners — top left
    d.line([(20,20),(120,20)], fill=(80,200,80,220), width=3)
    d.line([(20,20),(20,120)], fill=(80,200,80,220), width=3)
    # top right
    d.line([(W-20,20),(W-120,20)], fill=(80,200,80,220), width=3)
    d.line([(W-20,20),(W-20,120)], fill=(80,200,80,220), width=3)
    # bottom left
    d.line([(20,H-20),(120,H-20)], fill=(80,200,80,220), width=3)
    d.line([(20,H-20),(20,H-120)], fill=(80,200,80,220), width=3)
    # bottom right
    d.line([(W-20,H-20),(W-120,H-20)], fill=(80,200,80,220), width=3)
    d.line([(W-20,H-20),(W-20,H-120)], fill=(80,200,80,220), width=3)
    # Intel strip
    _rounded_rect(img, 0, 0, W, 90, 0, (0,20,0,200))
    _stamp_text(img, "FLEET INTEL  |  TUDOR NAVY  |  1588", 30, 14, fnt_sm, color=(80,255,80), outline=(0,0,0))
    # Bottom
    _rounded_rect(img, 0, H-140, W, H, 0, (0,20,0,210))
    _stamp_text(img, "PATROLLING EVERY OCEAN", 30, H-128, fnt_title, color=(150,255,150), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_industrial_orange(path: Path):
    """Industrial revolution — orange steam glow, year stamp"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 44)
    fnt_title = _font("impact.ttf", 72)
    fnt_year = _font("impact.ttf", 96)
    # Bottom dark gradient strip
    _rounded_rect(img, 0, H-260, W, H, 0, (20,8,0,220))
    # Orange accent line
    d = ImageDraw.Draw(img)
    d.rectangle([0, H-264, W, H-258], fill=(255,120,20,240))
    _stamp_text(img, "THE INDUSTRIAL REVOLUTION", 30, H-240, fnt_sm, color=(255,160,40), outline=(0,0,0))
    _stamp_text(img, "STEAM REWROTE HISTORY", 30, H-180, fnt_title, color=(255,220,160), outline=(0,0,0))
    # Top year badge
    _rounded_rect(img, 30, 30, 350, 160, 16, (255,100,20,220))
    _stamp_text(img, "1760s", 50, 40, fnt_year, color=(255,255,200), outline=(80,30,0))
    img.save(str(path), "PNG")

def make_overlay_factory_title(path: Path):
    """Workshop of the World — title card with amber glow"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 46)
    fnt_title = _font("impact.ttf", 80)
    # Amber vignette strip bottom
    _rounded_rect(img, 0, H-210, W, H, 0, (30,15,0,230))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H-214, W, H-208], fill=(200,100,0,240))
    _stamp_text(img, "WORKSHOP OF THE WORLD", 30, H-195, fnt_title, color=(255,200,80), outline=(60,30,0))
    _stamp_text(img, "ENGLAND — 1800s", 30, H-110, fnt_sm, color=(220,180,100), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_countup_globe(path: Path, count_str="35,000,000 km²"):
    """Empire size countup style card"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 44)
    fnt_num = _font("impact.ttf", 100)
    fnt_label = _font("impact.ttf", 56)
    # Semi-transparent top panel
    _rounded_rect(img, 30, 40, W-30, 300, 20, (0,0,0,200))
    _stamp_text(img, "EMPIRE SIZE", 60, 50, fnt_sm, color=(180,220,255), outline=(0,0,0))
    _stamp_text(img, count_str, 60, 100, fnt_num, color=(80,220,255), outline=(0,0,0))
    _stamp_text(img, "LARGEST EMPIRE IN HISTORY", 60, 218, fnt_label, color=(255,255,255), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_subjects_count(path: Path, count_str="400,000,000"):
    """Subjects population card"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 44)
    fnt_num = _font("impact.ttf", 90)
    fnt_label = _font("impact.ttf", 52)
    _rounded_rect(img, 30, 40, W-30, 280, 20, (0,0,0,210))
    _stamp_text(img, "POPULATION UNDER CROWN", 50, 50, fnt_sm, color=(255,200,100), outline=(0,0,0))
    _stamp_text(img, count_str, 50, 100, fnt_num, color=(255,180,40), outline=(0,0,0))
    _stamp_text(img, "400 MILLION PEOPLE", 50, 208, fnt_label, color=(255,255,255), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_war_bw(path: Path):
    """WWII newspaper headline — high contrast black and white treatment hint"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 44)
    fnt_headline = _font("impact.ttf", 76)
    # Newspaper top banner
    _rounded_rect(img, 0, 0, W, 130, 0, (10,10,10,230))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 126, W, 130], fill=(255,255,255,200))
    _stamp_text(img, "THE LONDON TIMES  |  WAR EDITION", 30, 8, fnt_sm, color=(255,255,255), outline=(0,0,0))
    _stamp_text(img, "1939 — 1945", 30, 60, fnt_sm, color=(200,200,200), outline=(0,0,0))
    # Bottom strip
    _rounded_rect(img, 0, H-180, W, H, 0, (10,10,10,220))
    _stamp_text(img, "TWO WARS. ONE EMPIRE SHATTERED.", 30, H-165, fnt_headline, color=(255,255,255), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_ve_day_gold(path: Path):
    """VE Day victory gold celebration"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 48)
    fnt_title = _font("impact.ttf", 88)
    # Gold top banner
    _rounded_rect(img, 0, 0, W, 140, 0, (80,60,0,220))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 136, W, 140], fill=(255,220,0,255))
    _stamp_text(img, "V-E DAY  |  8 MAY 1945", 40, 14, fnt_sm, color=(255,220,60), outline=(0,0,0))
    _stamp_text(img, "VICTORY IN EUROPE", 40, 72, fnt_sm, color=(255,255,200), outline=(0,0,0))
    # Bottom
    _rounded_rect(img, 0, H-170, W, H, 0, (40,30,0,220))
    _stamp_text(img, "EMPIRE SURVIVES — BARELY", 30, H-155, fnt_title, color=(255,230,80), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_legacy_purple(path: Path):
    """Parliament / legacy royal purple"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 44)
    fnt_title = _font("impact.ttf", 76)
    fnt_num = _font("impact.ttf", 100)
    _rounded_rect(img, 0, 0, W, 110, 0, (40,0,80,220))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 106, W, 110], fill=(160,80,255,255))
    _stamp_text(img, "WESTMINSTER — THE MOTHER OF PARLIAMENTS", 20, 14, fnt_sm, color=(200,140,255), outline=(0,0,0))
    # Bottom data card
    _rounded_rect(img, 30, H-280, W-30, H-20, 20, (20,0,50,220))
    _stamp_text(img, "ENGLISH SPEAKERS TODAY", 60, H-265, fnt_sm, color=(180,130,255), outline=(0,0,0))
    _stamp_text(img, "2 BILLION+", 60, H-215, fnt_num, color=(200,160,255), outline=(0,0,0))
    _stamp_text(img, "THE EMPIRE LIVES IN LANGUAGE", 60, H-120, fnt_title, color=(220,200,255), outline=(0,0,0))
    img.save(str(path), "PNG")

def make_overlay_cta_subscribe(path: Path):
    """Subscribe CTA — red badge + unsealed files hook"""
    img = Image.new("RGBA", (W, H), (0,0,0,0))
    fnt_sm = _font("impact.ttf", 48)
    fnt_title = _font("impact.ttf", 84)
    fnt_big = _font("impact.ttf", 100)
    # Red subscribe badge
    _rounded_rect(img, 80, H-450, W-80, H-280, 24, (220,20,20,240))
    _stamp_text(img, "LIKE & SUBSCRIBE", 120, H-440, fnt_title, color=(255,255,80), outline=(0,0,0))
    _stamp_text(img, "TO UNCOVER THE", 120, H-350, fnt_sm, color=(255,220,220), outline=(0,0,0))
    # Unsealed files brand
    _rounded_rect(img, 0, H-260, W, H, 0, (0,0,0,230))
    _stamp_text(img, "UNSEALED FILES", 60, H-240, fnt_big, color=(255,80,80), outline=(0,0,0))
    img.save(str(path), "PNG")

OVERLAY_BUILDERS = {
    "HOOK_MAP":        make_overlay_hook_map,
    "ROMAN_DOSSIER":   make_overlay_roman_dossier,
    "DARK_NORSE":      make_overlay_dark_norse,
    "BATTLE_BREAKING": make_overlay_battle_breaking,
    "ARCHIVAL_DOC":    make_overlay_archival_doc,
    "LAW_SEAL":        make_overlay_law_seal,
    "NAVY_HUD":        make_overlay_navy_hud,
    "INDUSTRIAL_ORANGE": make_overlay_industrial_orange,
    "FACTORY_TITLE":   make_overlay_factory_title,
    "COUNTUP_GLOBE":   make_overlay_countup_globe,
    "SUBJECTS_COUNT":  make_overlay_subjects_count,
    "WAR_BW":          make_overlay_war_bw,
    "VE_DAY_GOLD":     make_overlay_ve_day_gold,
    "LEGACY_PURPLE":   make_overlay_legacy_purple,
    "CTA_SUBSCRIBE":   make_overlay_cta_subscribe,
}

# ─────────────────────────────────────────────────────────────
#  COLOR GRADE PER DESIGN  (FFmpeg eq + colorchannelmixer)
# ─────────────────────────────────────────────────────────────
GRADE_FILTER = {
    "HOOK_MAP":        "eq=saturation=1.3:contrast=1.1,colorchannelmixer=rr=1.1:gg=0.9:bb=0.7",
    "ROMAN_DOSSIER":   "eq=saturation=0.5:brightness=-0.05,colorchannelmixer=rr=1.2:gg=1.0:bb=0.7",
    "DARK_NORSE":      "eq=saturation=0.8:brightness=-0.12:contrast=1.15,colorchannelmixer=rr=0.8:gg=0.9:bb=1.3",
    "BATTLE_BREAKING": "eq=saturation=0.6:contrast=1.3:brightness=-0.08",
    "ARCHIVAL_DOC":    "eq=saturation=0.3:brightness=0.04,colorchannelmixer=rr=1.2:gg=1.05:bb=0.75",
    "LAW_SEAL":        "eq=saturation=0.4:brightness=0.02,colorchannelmixer=rr=1.1:gg=1.0:bb=0.8",
    "NAVY_HUD":        "eq=saturation=0.9:contrast=1.1,colorchannelmixer=rr=0.85:gg=1.0:bb=0.85",
    "INDUSTRIAL_ORANGE": "eq=saturation=1.1:brightness=-0.1:contrast=1.2,colorchannelmixer=rr=1.2:gg=0.95:bb=0.7",
    "FACTORY_TITLE":   "eq=saturation=0.8:brightness=-0.15,colorchannelmixer=rr=1.1:gg=0.9:bb=0.75",
    "COUNTUP_GLOBE":   "eq=saturation=1.2:contrast=1.1,colorchannelmixer=rr=0.85:gg=0.9:bb=1.2",
    "SUBJECTS_COUNT":  "eq=saturation=1.1:contrast=1.05",
    "WAR_BW":          "eq=saturation=0.0:contrast=1.4:brightness=-0.05",
    "VE_DAY_GOLD":     "eq=saturation=1.3:brightness=0.06,colorchannelmixer=rr=1.1:gg=1.05:bb=0.8",
    "LEGACY_PURPLE":   "eq=saturation=1.1:brightness=-0.06,colorchannelmixer=rr=0.9:gg=0.8:bb=1.15",
    "CTA_SUBSCRIBE":   "eq=saturation=1.2:contrast=1.2:brightness=-0.04",
}

# ─────────────────────────────────────────────────────────────
#  KEN BURNS MOTION  (FFmpeg zoompan filter)
# ─────────────────────────────────────────────────────────────
def zoompan_filter(motion: str, duration: float) -> str:
    nf = max(1, int(duration * FPS))
    s = f"s={W}x{H}"
    d = f"d={nf}"
    if motion == "zoom_in":
        return f"zoompan=z='min(zoom+0.0012,1.5)':{d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{s},fps={FPS}"
    elif motion == "zoom_out":
        return f"zoompan=z='if(eq(on\\,1)\\,1.5\\,max(zoom-0.0012\\,1.0))':{d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{s},fps={FPS}"
    elif motion == "pan_right":
        return f"zoompan=z='1.25':{d}:x='iw*on/{nf}/4':y='ih/2-(ih/zoom/2)':{s},fps={FPS}"
    elif motion == "pan_left":
        return f"zoompan=z='1.25':{d}:x='iw/4-iw*on/{nf}/4':y='ih/2-(ih/zoom/2)':{s},fps={FPS}"
    elif motion == "crash_zoom":
        return f"zoompan=z='min(zoom+0.003,2.0)':{d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{s},fps={FPS}"
    return f"zoompan=z='1.0':{d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':{s},fps={FPS}"

# ─────────────────────────────────────────────────────────────
#  TTS + WORD TIMESTAMPS
# ─────────────────────────────────────────────────────────────
async def generate_tts(out_wav: Path, out_words: Path):
    print(f"[TTS] Generating narration: {VOICE} @ {RATE}")
    communicate = edge_tts.Communicate(SCRIPT, VOICE, rate=RATE)
    words = []
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            words.append({
                "word": chunk["text"],
                "start": chunk["offset"] / 10_000_000,
                "end":   (chunk["offset"] + chunk["duration"]) / 10_000_000,
            })
    # Write raw audio
    raw_mp3 = out_wav.with_suffix(".mp3")
    raw_mp3.write_bytes(b"".join(audio_chunks))
    # Convert to WAV
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(raw_mp3), "-ar", "44100", "-ac", "1", str(out_wav)],
        check=True, capture_output=True
    )
    raw_mp3.unlink(missing_ok=True)
    out_words.write_text(json.dumps(words, indent=2), encoding="utf-8")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out_wav)],
        capture_output=True, text=True
    )
    dur = float(probe.stdout.strip())
    print(f"[TTS] Duration: {dur:.2f}s")
    return dur, words

# ─────────────────────────────────────────────────────────────
#  ASS SUBTITLE GENERATOR (Hormozi style — Impact + green)
# ─────────────────────────────────────────────────────────────
def generate_ass(words: list, out_ass: Path, words_per_line: int = 3):
    """Word-by-word with neon green active word, Impact font, centered lower third."""
    header = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,78,&H00FFFFFF,&H0000FF00,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,4,2,40,40,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = t % 60
        return f"{h}:{m:02d}:{s:06.3f}"

    def group(words_chunk):
        return [w["word"] for w in words_chunk]

    events = []
    i = 0
    while i < len(words):
        chunk = words[i:i+words_per_line]
        chunk_words = [w["word"] for w in chunk]
        start = chunk[0]["start"]
        end   = chunk[-1]["end"]

        for j, w in enumerate(chunk):
            ws = w["start"]
            we = w["end"]
            parts = []
            for k, cw in enumerate(chunk_words):
                if k == j:
                    parts.append(r"{\c&H0000FF00\b1}" + cw.upper() + r"{\rDefault}")
                else:
                    parts.append(r"{\c&H00FFFFFF}" + cw.upper())
            line = " ".join(parts)
            events.append(f"Dialogue: 0,{ts(ws)},{ts(we)},Default,,0,0,0,,{line}")

        i += words_per_line

    out_ass.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    print(f"[SUB] Wrote {len(events)} subtitle events -> {out_ass.name}")

# ─────────────────────────────────────────────────────────────
#  SCENE TIMINGS  (from narration duration)
# ─────────────────────────────────────────────────────────────
def compute_timings(total_dur: float) -> dict:
    raw = json.loads(TIMINGS.read_text(encoding="utf-8"))
    # Scale timings proportionally to actual TTS duration
    old_total = max(v["end"] for v in raw.values())
    scale = total_dur / old_total
    scaled = {}
    for k, v in raw.items():
        scaled[k] = {
            "scene_id": k,
            "start": v["start"] * scale,
            "end":   v["end"]   * scale,
            "duration": v["duration"] * scale,
        }
    return scaled

# ─────────────────────────────────────────────────────────────
#  SCENE RENDER  (FFmpeg-native, no PIL frame loop)
# ─────────────────────────────────────────────────────────────
def render_scene(scene_id, asset_name, motion, design, duration, temp_dir, overlay_dir):
    asset = ASSETS / asset_name
    out   = temp_dir / f"{scene_id}.mp4"
    overlay_png = overlay_dir / f"{design}.png"

    is_video = asset.suffix.lower() == ".mp4"
    grade = GRADE_FILTER.get(design, "eq=saturation=1.0")
    kb = zoompan_filter(motion, duration)

    if is_video:
        input_args = ["-stream_loop", "-1", "-i", str(asset)]
    else:
        input_args = ["-loop", "1", "-i", str(asset)]

    # vf: scale+crop → grade → zoompan → overlay PNG
    overlay_esc = str(overlay_png.resolve()).replace("\\", "/").replace(":", "\\:")
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},"
        f"{grade},"
        f"{kb}"
    )
    # Compose overlay on top
    cmd = (
        ["ffmpeg", "-y"]
        + input_args
        + ["-i", str(overlay_png)]
        + [
            "-filter_complex",
            f"[0:v]{vf}[bg];[bg][1:v]overlay=0:0[out]",
            "-map", "[out]",
            "-t", f"{duration:.3f}",
            "-r", str(FPS),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-an",
            str(out)
        ]
    )
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"  [WARN] Overlay failed for {scene_id}, trying without overlay")
        print(f"  STDERR: {res.stderr[-600:]}")
        # Fallback: no overlay
        cmd2 = (
            ["ffmpeg", "-y"]
            + input_args
            + [
                "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{grade},{kb}",
                "-t", f"{duration:.3f}",
                "-r", str(FPS),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-an",
                str(out)
            ]
        )
        res2 = subprocess.run(cmd2, capture_output=True, text=True)
        if res2.returncode != 0:
            raise RuntimeError(f"Scene {scene_id} failed: {res2.stderr[-400:]}")
    kb_size = out.stat().st_size // 1024
    print(f"  [OK] {scene_id} ({duration:.2f}s) -> {out.name} ({kb_size}KB)")
    return out

# ─────────────────────────────────────────────────────────────
#  AUDIO MIX
# ─────────────────────────────────────────────────────────────
def mix_audio(narration: Path, out_wav: Path, total_dur: float):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(narration),
        "-stream_loop", "-1",
        "-i", str(MUSIC),
        "-filter_complex",
        (
            "[0:a]volume=1.0,acompressor=threshold=0.1:ratio=4:attack=5:release=200[voice];"
            "[1:a]volume=0.16[music];"
            "[voice][music]amix=inputs=2:duration=first:dropout_transition=2[out]"
        ),
        "-map", "[out]",
        "-t", str(total_dur + 0.5),
        "-ar", "44100",
        "-ac", "2",
        str(out_wav),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Audio mix failed: {res.stderr[-500:]}")
    print(f"[AUDIO] Mixed -> {out_wav.name}")

# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
async def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    TEMP.mkdir(parents=True, exist_ok=True)
    overlay_dir = TEMP / "overlays"
    overlay_dir.mkdir(exist_ok=True)

    print("=" * 64)
    print(" ENGLAND DOCUMENTARY — v3 Render Pipeline")
    print("=" * 64)

    # 1. TTS
    narration = RUN_DIR / "narration.wav"
    words_path = RUN_DIR / "word_timestamps.json"
    if narration.exists():
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(narration)],
            capture_output=True, text=True
        )
        total_dur = float(probe.stdout.strip())
        words = json.loads(words_path.read_text(encoding="utf-8")) if words_path.exists() else []
        print(f"[TTS] Reusing existing narration ({total_dur:.2f}s)")
    else:
        total_dur, words = await generate_tts(narration, words_path)

    # 2. ASS subtitles
    ass_path = RUN_DIR / "captions.ass"
    if words:
        generate_ass(words, ass_path)
    else:
        # fallback: copy from old run
        import shutil
        shutil.copy(OLD_RUN / "03_captions.ass", ass_path)
        print("[SUB] Copied previous captions.ass")

    # 3. Scene timings
    timings = compute_timings(total_dur)
    print(f"[TIMING] {len(timings)} scenes, total={total_dur:.2f}s")

    # 4. Build overlay PNGs
    print("[OVERLAY] Building design overlays...")
    for design_key, builder in OVERLAY_BUILDERS.items():
        png = overlay_dir / f"{design_key}.png"
        builder(png)
    print(f"  [OK] {len(OVERLAY_BUILDERS)} overlay PNGs generated")

    # 5. Render scenes
    print("[PHASE 1] Rendering scene clips (FFmpeg-native)...")
    seg_paths = []
    for scene_id, asset_name, motion, design in SCENES:
        t = timings.get(scene_id, {})
        duration = t.get("duration", 3.5)
        duration = max(1.0, duration)
        path = render_scene(scene_id, asset_name, motion, design, duration, TEMP, overlay_dir)
        seg_paths.append(path)

    # 6. Concatenate
    print("[PHASE 2] Concatenating clips...")
    concat_txt = TEMP / "concat.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for p in seg_paths:
            clean = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{clean}'\n")
    raw_video = TEMP / "raw_video.mp4"
    res = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(raw_video)
    ], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Concat failed: {res.stderr[-400:]}")
    print(f"  [OK] Raw video: {raw_video.stat().st_size // 1024}KB")

    # 7. Mix audio
    print("[PHASE 3] Mixing audio...")
    mixed_audio = RUN_DIR / "audio_mix.wav"
    mix_audio(narration, mixed_audio, total_dur)

    # 8. Burn subtitles + mux
    print("[PHASE 4] Burning subtitles + final mux...")
    final_out = RUN_DIR / "10_england_v3_final.mp4"
    # Escape path for Windows FFmpeg subtitles filter
    ass_esc = str(ass_path.resolve()).replace("\\", "/")
    drive, rest = ass_esc[0], ass_esc[2:]
    ass_esc = drive + "\\:" + rest

    cmd_final = [
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-i", str(mixed_audio),
        "-vf", f"subtitles='{ass_esc}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        "-shortest",
        str(final_out)
    ]
    res = subprocess.run(cmd_final, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[WARN] Subtitle burn failed, trying without: {res.stderr[-300:]}")
        cmd_no_sub = [
            "ffmpeg", "-y",
            "-i", str(raw_video),
            "-i", str(mixed_audio),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-shortest",
            str(final_out)
        ]
        subprocess.run(cmd_no_sub, check=True)

    # 9. Probe final
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
         "-of", "default=noprint_wrappers=1", str(final_out)],
        capture_output=True, text=True
    )
    print("=" * 64)
    print(f"[DONE] {final_out}")
    for line in probe.stdout.strip().splitlines():
        print(f"   {line}")
    print("=" * 64)

    # 10. Extract verification frames
    times = [1.5, 5.0, 10.0, 18.0, 25.0, 33.0, 41.0, 48.0, 53.0]
    for t in times:
        frame_out = RUN_DIR / f"frame_{int(t):02d}s.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(t),
            "-i", str(final_out), "-vframes", "1", "-q:v", "2", str(frame_out)
        ], capture_output=True)
    print(f"[VERIFY] Extracted {len(times)} frames")

if __name__ == "__main__":
    asyncio.run(main())
