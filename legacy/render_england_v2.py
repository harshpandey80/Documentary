"""
render_england_v2.py - History of England Remastered
Complete render pipeline: visuals + narration + Hormozi subtitles + audio mix.

Pipeline:
  1. Read 02_scene_timings.json for timing data
  2. Compose each scene: background video/image + Ken Burns + text overlay
  3. Concat all scene clips
  4. Mix narration (voice 1.0) over music bed (ducked -24dB during speech)
  5. Burn Hormozi word-by-word subtitles
  6. Output: 09_history_of_england_remastered.mp4 (vertical 1080x1920, <60s)

Requires: ffmpeg on PATH, Pillow, soundfile
"""

import io
import sys
# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import json
import math
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Paths ──────────────────────────────────────────────────────────────────────
RUN_DIR   = Path(__file__).parent
ASSETS    = RUN_DIR / "curated_assets"
NARRATION = RUN_DIR / "02_narration.wav"
TIMINGS   = RUN_DIR / "02_scene_timings.json"
WORDS_JSON= RUN_DIR / "02_word_timestamps.json"
CLIPS_DIR = RUN_DIR / "scene_clips"
FINAL_OUT = RUN_DIR / "09_history_of_england_remastered.mp4"
MUSIC_BED = Path(r"c:/Users/Harsh Pandey/OneDrive/Desktop/documentry-AI/assets/music")

CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# ── Canvas ────────────────────────────────────────────────────────────────────
W, H, FPS = 1080, 1920, 30   # Vertical 9:16

# ── Typography ─────────────────────────────────────────────────────────────────
FONT_BOLD = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
]
FONT_REG = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]

def load_font(size, bold=True):
    candidates = FONT_BOLD if bold else FONT_REG
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()

# ── Easing ─────────────────────────────────────────────────────────────────────
def ease_out_cubic(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3

def ease_in_out(x):
    x = max(0.0, min(1.0, x))
    return 3 * x * x - 2 * x * x * x

# ── Scene manifest ─────────────────────────────────────────────────────────────
# Maps scene_id → (asset_file, motion, overlay_type, overlay_args)
# motion: "zoomin" | "zoomout" | "pan_left" | "pan_right" | "pan_up"
# overlay_type: None | "countup" | "date_stamp" | "title_card"
SCENES = {
    "act1_s1": {
        "text": "How did this tiny island conquer twenty-four percent of Earth?",
        "bg": ASSETS / "british_empire_map.jpg",
        "motion": "zoomin",
        "overlay": "title_card",
        "overlay_args": {"title": "24%", "subtitle": "OF EARTH"},
        "filter_tint": None,
    },
    "act1_s2": {
        "text": "Two thousand years ago, Roman legions seized Britannia.",
        "bg": ASSETS / "roman_legions.mp4",
        "motion": "pan_right",
        "overlay": "date_stamp",
        "overlay_args": {"date": "43 AD", "label": "ROMAN INVASION"},
        "filter_tint": (180, 120, 60, 30),  # warm sepia tint
    },
    "act1_s3": {
        "text": "Saxons and Vikings battled over seven kingdoms.",
        "bg": ASSETS / "viking_ship.mp4",
        "motion": "pan_left",
        "overlay": None,
        "overlay_args": {},
        "filter_tint": (40, 60, 100, 40),
    },
    "act2_s1": {
        "text": "Until 1066. One Norman arrow to King Harold's eye.",
        "bg": ASSETS / "bayeux_tapestry_harold.jpg",
        "motion": "crash_zoom",
        "overlay": "date_stamp",
        "overlay_args": {"date": "1066", "label": "BATTLE OF HASTINGS"},
        "filter_tint": (80, 40, 20, 40),
    },
    "act2_s2": {
        "text": "William the Conqueror forged a unified crown.",
        "bg": ASSETS / "domesday_book.png",
        "motion": "zoomin",
        "overlay": None,
        "overlay_args": {},
        "filter_tint": (60, 45, 20, 50),
    },
    "act2_s3": {
        "text": "In 1215, Magna Carta restricted absolute royal tyranny.",
        "bg": ASSETS / "magna_carta.jpg",
        "motion": "pan_up",
        "overlay": "date_stamp",
        "overlay_args": {"date": "1215", "label": "MAGNA CARTA"},
        "filter_tint": (50, 40, 20, 40),
    },
    "act3_s1": {
        "text": "Henry the Eighth severed Rome, commissioning the Royal Navy.",
        "bg": ASSETS / "tudor_navy.mp4",
        "motion": "pan_right",
        "overlay": None,
        "overlay_args": {},
        "filter_tint": (30, 50, 80, 30),
    },
    "act3_s2": {
        "text": "In 1769, steam engines ignited the Industrial Revolution.",
        "bg": ASSETS / "steam_engine.mp4",
        "motion": "zoomin",
        "overlay": "date_stamp",
        "overlay_args": {"date": "1769", "label": "INDUSTRIAL REVOLUTION"},
        "filter_tint": (20, 20, 20, 60),
    },
    "act4_s1": {
        "text": "England became the workshop of the modern world.",
        "bg": ASSETS / "foundry_workshop.mp4",
        "motion": "pan_left",
        "overlay": None,
        "overlay_args": {},
        "filter_tint": (20, 20, 20, 50),
    },
    "act4_s2": {
        "text": "Thirty-five million square kilometers fell under one crown.",
        "bg": ASSETS / "british_empire_map.jpg",
        "motion": "zoomout",
        "overlay": "countup",
        "overlay_args": {"value": 35, "unit": "M KM²", "label": "UNDER ONE CROWN"},
        "filter_tint": (20, 30, 60, 40),
    },
    "act4_s3": {
        "text": "Four hundred million subjects. An empire where the sun never set.",
        "bg": ASSETS / "british_empire_map.jpg",
        "motion": "pan_right",
        "overlay": "countup",
        "overlay_args": {"value": 400, "unit": "M", "label": "SUBJECTS"},
        "filter_tint": (20, 30, 60, 50),
    },
    "act5_s1": {
        "text": "Two world wars bled the treasury dry.",
        "bg": ASSETS / "london_blitz_1940.jpg",
        "motion": "crash_zoom",
        "overlay": None,
        "overlay_args": {},
        "filter_tint": (10, 10, 10, 80),
    },
    "act5_s2": {
        "text": "By 1945, bankrupt and exhausted, colonies broke free.",
        "bg": ASSETS / "ve_day_crowd.mp4",
        "motion": "zoomin",
        "overlay": "date_stamp",
        "overlay_args": {"date": "1945", "label": "END OF EMPIRE"},
        "filter_tint": (20, 30, 50, 30),
    },
    "act6_s1": {
        "text": "Its language, law, and parliaments still govern billions.",
        "bg": ASSETS / "westminster_aerial.mp4",
        "motion": "pan_up",
        "overlay": "countup",
        "overlay_args": {"value": 2, "unit": "B+", "label": "GOVERNED BY ITS LEGACY"},
        "filter_tint": (10, 20, 40, 20),
    },
    "act6_s2": {
        "text": "Like and subscribe to uncover the unsealed files.",
        "bg": ASSETS / "big_ben_tower.mp4",
        "motion": "zoomin",
        "overlay": "cta",
        "overlay_args": {},
        "filter_tint": (5, 10, 30, 30),
    },
}


# ── Ken Burns motion filter ────────────────────────────────────────────────────
def ken_burns_filter(motion: str, duration: float) -> str:
    """Return FFmpeg zoompan filter string for the given motion type."""
    fps = FPS
    nframes = int(duration * fps)

    if motion == "zoomin":
        # Gentle zoom 1.0 → 1.12 from center
        return (
            f"zoompan=z='min(zoom+0.0004,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={nframes}:s={W}x{H}:fps={fps}"
        )
    elif motion == "zoomout":
        return (
            f"zoompan=z='if(lte(zoom,1.0),1.12,max(1.0,zoom-0.0004))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={nframes}:s={W}x{H}:fps={fps}"
        )
    elif motion == "crash_zoom":
        # Punch zoom: 1.0 → 1.25 fast then settle
        return (
            f"zoompan=z='min(zoom+0.0012,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={nframes}:s={W}x{H}:fps={fps}"
        )
    elif motion == "pan_left":
        return (
            f"zoompan=z='1.12':x='iw/2-(iw/zoom/2)+on*{W}/(zoom*{nframes}*0.5)'"
            f":y='ih/2-(ih/zoom/2)':d={nframes}:s={W}x{H}:fps={fps}"
        )
    elif motion == "pan_right":
        return (
            f"zoompan=z='1.12':x='iw/2-(iw/zoom/2)-on*{W}/(zoom*{nframes}*0.5)'"
            f":y='ih/2-(ih/zoom/2)':d={nframes}:s={W}x{H}:fps={fps}"
        )
    elif motion == "pan_up":
        return (
            f"zoompan=z='1.12':x='iw/2-(iw/zoom/2)'"
            f":y='ih/2-(ih/zoom/2)+on*{H}/(zoom*{nframes}*0.5)':d={nframes}:s={W}x{H}:fps={fps}"
        )
    else:
        return f"zoompan=z='1.0':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={nframes}:s={W}x{H}:fps={fps}"


# ── Text overlay helpers (PIL-based, burned in per scene) ──────────────────────
def draw_scene_overlay(frame_idx: int, total_frames: int, scene: dict,
                       timings: dict, words_in_scene: list) -> Image.Image:
    """Draw all overlay elements for one frame. Returns RGBA image."""
    t = frame_idx / FPS
    dur = total_frames / FPS

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # ── Top vignette gradient (cinematic letterbox look) ──────────────────────
    for y in range(200):
        alpha = int(180 * (1 - y / 200))
        d.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    # Bottom vignette
    for y in range(H - 300, H):
        alpha = int(200 * ((y - (H - 300)) / 300))
        d.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))

    # ── Date/Title overlay ─────────────────────────────────────────────────────
    ov = scene.get("overlay")
    args = scene.get("overlay_args", {})

    fade_t = 0.25
    a_in  = ease_in_out(min(1.0, t / fade_t))
    a_out = ease_in_out(min(1.0, (dur - t) / fade_t))
    alpha_ov = min(a_in, a_out)

    if ov == "date_stamp":
        _draw_date_stamp(d, args.get("date",""), args.get("label",""), alpha_ov)
    elif ov == "countup":
        _draw_countup(d, t, dur, args.get("value", 0), args.get("unit",""), args.get("label",""), alpha_ov)
    elif ov == "title_card":
        _draw_title_card(d, args.get("title",""), args.get("subtitle",""), alpha_ov)
    elif ov == "cta":
        _draw_cta(d, alpha_ov)

    # ── Hormozi subtitles ─────────────────────────────────────────────────────
    scene_start = timings["start"]
    abs_t = scene_start + t
    _draw_hormozi_subtitles(d, words_in_scene, abs_t, t, dur)

    return canvas


def _draw_date_stamp(d: ImageDraw.Draw, date: str, label: str, alpha: float):
    """Forensic-style date stamp in top-left with accent line."""
    if alpha <= 0:
        return
    a = int(255 * alpha)
    f_big = load_font(88)
    f_lbl = load_font(42)
    pad = 48

    # Accent bar
    d.rectangle([pad, 80, pad + 6, 180], fill=(255, 176, 46, a))

    # Date text
    d.text((pad + 22, 80), date, font=f_big, fill=(255, 255, 255, a))
    if label:
        d.text((pad + 22, 176), label, font=f_lbl, fill=(170, 210, 240, a))


def _draw_countup(d: ImageDraw.Draw, t: float, dur: float,
                  value: float, unit: str, label: str, alpha: float):
    """Animated count-up number with panel."""
    if alpha <= 0:
        return
    a = int(255 * alpha)
    count_time = min(dur * 0.7, 2.0)
    progress = ease_out_cubic(min(1.0, t / count_time))
    shown = int(round(value * progress))
    number_text = f"{shown:,}"

    f_num = load_font(160)
    f_unit = load_font(60)
    f_lbl = load_font(44)

    # Panel
    panel_x, panel_y = 60, H // 2 - 200
    panel_w, panel_h = W - 120, 340
    panel_rgba = (6, 12, 20, int(165 * alpha))
    _draw_rounded_rect(d, panel_x, panel_y, panel_w, panel_h, 28, panel_rgba)

    # Number
    slide = int((1 - ease_out_cubic(min(1.0, t / 0.4))) * 30)
    nb = d.textbbox((0, 0), number_text, font=f_num)
    ub = d.textbbox((0, 0), unit, font=f_unit) if unit else (0, 0, 0, 0)
    row_w = (nb[2] - nb[0]) + (16 + ub[2] - ub[0] if unit else 0)
    rx = W // 2 - row_w // 2
    ny = panel_y + 30 + slide
    d.text((rx - nb[0], ny - nb[1]), number_text, font=f_num, fill=(255, 255, 255, a))
    if unit:
        uy = ny + (nb[3] - nb[1]) - (ub[3] - ub[1])
        d.text((rx + (nb[2] - nb[0]) + 16 - ub[0], uy - ub[1]), unit, font=f_unit, fill=(255, 176, 46, a))

    # Progress bar
    bar_y = panel_y + 250
    bar_w = panel_w - 80
    bx = panel_x + 40
    d.rounded_rectangle([bx, bar_y, bx + int(bar_w * progress), bar_y + 8],
                        radius=4, fill=(255, 176, 46, a))

    # Label
    if label:
        lb = d.textbbox((0, 0), label, font=f_lbl)
        d.text((W // 2 - (lb[2] - lb[0]) // 2 - lb[0], bar_y + 22 - lb[1]),
               label, font=f_lbl, fill=(170, 210, 240, a))


def _draw_title_card(d: ImageDraw.Draw, title: str, subtitle: str, alpha: float):
    """Big centered title card for hook frame."""
    if alpha <= 0:
        return
    a = int(255 * alpha)
    f_big = load_font(220)
    f_sub = load_font(64)

    tb = d.textbbox((0, 0), title, font=f_big)
    tw = tb[2] - tb[0]
    tx = W // 2 - tw // 2 - tb[0]
    ty = H // 2 - (tb[3] - tb[1]) // 2 - tb[1]

    # Glow shadow
    for dx, dy in [(-3, -3), (3, 3), (-3, 3), (3, -3)]:
        d.text((tx + dx, ty + dy), title, font=f_big, fill=(255, 120, 0, int(a * 0.4)))
    d.text((tx, ty), title, font=f_big, fill=(255, 230, 60, a))

    if subtitle:
        sb = d.textbbox((0, 0), subtitle, font=f_sub)
        sx = W // 2 - (sb[2] - sb[0]) // 2 - sb[0]
        sy = ty + (tb[3] - tb[1]) + 20
        d.text((sx, sy), subtitle, font=f_sub, fill=(200, 200, 200, a))


def _draw_cta(d: ImageDraw.Draw, alpha: float):
    """Like & Subscribe CTA card."""
    if alpha <= 0:
        return
    a = int(255 * alpha)
    f_cta = load_font(72)
    f_sub = load_font(44)

    line1 = "👍 LIKE & SUBSCRIBE"
    line2 = "for the unsealed files"

    lb1 = d.textbbox((0, 0), line1, font=f_cta)
    lx1 = W // 2 - (lb1[2] - lb1[0]) // 2 - lb1[0]
    ly1 = H - 520
    d.text((lx1, ly1), line1, font=f_cta, fill=(255, 230, 30, a))

    lb2 = d.textbbox((0, 0), line2, font=f_sub)
    lx2 = W // 2 - (lb2[2] - lb2[0]) // 2 - lb2[0]
    d.text((lx2, ly1 + (lb1[3] - lb1[1]) + 16), line2, font=f_sub,
           fill=(200, 200, 200, a))


def _draw_hormozi_subtitles(d: ImageDraw.Draw, words: list, abs_t: float,
                            local_t: float, dur: float):
    """Word-by-word Hormozi subtitles: white + neon green active word."""
    if not words:
        return

    SAFE_BOTTOM = H - 200   # above platform UI
    FONT_SIZE = 68
    LINE_H = 88
    MAX_LINE_W = W - 100
    ACTIVE_COLOR = (0, 255, 0, 255)
    BASE_COLOR   = (255, 255, 255, 230)
    SHADOW_COLOR = (0, 0, 0, 180)

    f = load_font(FONT_SIZE)

    # Group words into lines of ≤ MAX_LINE_W px
    lines = []
    current_line = []
    current_w = 0
    for w in words:
        wb = d.textbbox((0, 0), w["word"] + " ", font=f)
        ww = wb[2] - wb[0]
        if current_w + ww > MAX_LINE_W and current_line:
            lines.append(current_line)
            current_line = [w]
            current_w = ww
        else:
            current_line.append(w)
            current_w += ww
    if current_line:
        lines.append(current_line)

    # Show only the last 2 lines at a time (current + previous)
    # Find which line contains the active word
    active_line_idx = 0
    for li, line in enumerate(lines):
        for w in line:
            if w["start"] <= abs_t < w["end"]:
                active_line_idx = li
                break

    show_lines = lines[max(0, active_line_idx - 1): active_line_idx + 1]
    n_lines = len(show_lines)
    total_h = n_lines * LINE_H
    start_y = SAFE_BOTTOM - total_h

    for li, line in enumerate(show_lines):
        # Measure total line width
        total_line_w = sum(
            (d.textbbox((0, 0), w["word"] + " ", font=f)[2] -
             d.textbbox((0, 0), w["word"] + " ", font=f)[0])
            for w in line
        )
        x = (W - total_line_w) // 2
        y = start_y + li * LINE_H

        for w in line:
            wb = d.textbbox((0, 0), w["word"] + " ", font=f)
            ww = wb[2] - wb[0]
            is_active = w["start"] <= abs_t < w["end"]
            color = ACTIVE_COLOR if is_active else BASE_COLOR
            # Shadow
            d.text((x - wb[0] + 2, y - wb[1] + 2), w["word"], font=f, fill=SHADOW_COLOR)
            d.text((x - wb[0], y - wb[1]), w["word"], font=f, fill=color)
            x += ww


def _draw_rounded_rect(d, x, y, w, h, r, fill):
    d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill)


# ── Scene renderer ─────────────────────────────────────────────────────────────
def render_scene(scene_id: str, scene: dict, timings: dict,
                 all_words: list) -> Path:
    """Render one scene clip to CLIPS_DIR/{scene_id}.mp4"""
    out = CLIPS_DIR / f"{scene_id}.mp4"
    duration = timings["duration"]
    n_frames = int(round(duration * FPS))
    bg_path = scene["bg"]

    # Filter words for this scene
    t_start = timings["start"]
    t_end   = timings["end"]
    scene_words = [w for w in all_words if w["end"] > t_start and w["start"] < t_end]

    # ── Step 1: Prepare background source ─────────────────────────────────────
    is_video = str(bg_path).lower().endswith((".mp4", ".mov", ".webm"))

    # ── Step 2: Build FFmpeg filter graph ─────────────────────────────────────
    motion_filter = ken_burns_filter(scene["motion"], duration)

    if is_video:
        # Loop-trim video to duration, apply Ken Burns, scale to vertical
        bg_cmd_part = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-stream_loop", "-1",
            "-i", str(bg_path),
            "-t", str(duration),
            "-vf", (
                f"scale={max(W, H)}:{max(W, H)}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},"
                f"{motion_filter}"
            ),
            "-r", str(FPS),
            "-frames:v", str(n_frames),
            "-pix_fmt", "yuv420p",
            "-an",
            "-f", "rawvideo",
            "pipe:1"
        ]
    else:
        # Static image: decode once, apply Ken Burns via zoompan
        bg_cmd_part = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-loop", "1",
            "-i", str(bg_path),
            "-t", str(duration),
            "-vf", (
                f"scale={max(W, H)}:{max(W, H)}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},"
                f"{motion_filter}"
            ),
            "-r", str(FPS),
            "-frames:v", str(n_frames),
            "-pix_fmt", "yuv420p",
            "-an",
            "-f", "rawvideo",
            "pipe:1"
        ]

    print(f"  [BG] extracting {n_frames} frames from {bg_path.name}...")
    bg_proc = subprocess.Popen(bg_cmd_part, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # ── Step 3: Read BG frames, compose overlays, write final ─────────────────
    frame_size = W * H * 3  # yuv420p... actually RGB after decode
    # We'll use rawvideo rgba for the overlay pipe
    # Actually: read YUV420 from bg, convert to PIL, composite, write RGBA to encoder

    # Simpler: decode bg to RGBA frames via ffmpeg rawvideo
    bg_rgba_cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        *((["-stream_loop", "-1"] if is_video else ["-loop", "1"])),
        "-i", str(bg_path),
        "-t", str(duration),
        "-vf", (
            f"scale={max(W, H)}:{max(W, H)}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"{motion_filter}"
        ),
        "-r", str(FPS),
        "-frames:v", str(n_frames),
        "-pix_fmt", "rgb24",
        "-an",
        "-f", "rawvideo",
        "pipe:1"
    ]

    bg_proc.kill()  # kill the previous attempt
    bg_proc.wait()

    print(f"  [COMPOSE] {scene_id}: {n_frames} frames @ {FPS}fps ({duration:.2f}s)")
    bg_proc = subprocess.Popen(bg_rgba_cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL)

    # Encoder: RGBA rawvideo → H264 MP4
    enc_cmd = [
        "ffmpeg", "-y", "-loglevel", "warning",
        "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out)
    ]
    enc_proc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)

    frame_bytes = W * H * 3  # rgb24
    tint = scene.get("filter_tint")  # (R,G,B,A) additive tint or None

    for fi in range(n_frames):
        raw = bg_proc.stdout.read(frame_bytes)
        if len(raw) < frame_bytes:
            # pad last frames if BG ran out
            raw = raw + b'\x00' * (frame_bytes - len(raw))

        # Convert RGB bytes to PIL RGBA
        bg_img = Image.frombytes("RGB", (W, H), raw).convert("RGBA")

        # Apply tint (cinematic color grade)
        if tint:
            tint_layer = Image.new("RGBA", (W, H), tint)
            bg_img = Image.alpha_composite(bg_img, tint_layer)

        # Composite overlay
        overlay = draw_scene_overlay(fi, n_frames, scene, timings, scene_words)
        composed = Image.alpha_composite(bg_img, overlay)

        enc_proc.stdin.write(composed.tobytes())

    enc_proc.stdin.close()
    enc_proc.wait()
    bg_proc.kill()
    bg_proc.wait()

    if not out.exists() or out.stat().st_size < 1000:
        raise RuntimeError(f"Scene {scene_id} render failed → {out}")

    print(f"  [OK] {scene_id} -> {out.name} ({out.stat().st_size // 1024}KB)")
    return out


# ── Audio mix ──────────────────────────────────────────────────────────────────
def find_music_bed() -> Path | None:
    """Find a suitable ambient music bed in assets/music/."""
    candidates = [
        Path("c:/Users/Harsh Pandey/OneDrive/Desktop/documentry-AI/assets/music"),
        Path("c:/Users/Harsh Pandey/OneDrive/Desktop/documentry-AI/assets"),
    ]
    exts = {".mp3", ".wav", ".ogg", ".m4a"}
    for folder in candidates:
        if folder.exists():
            for f in folder.iterdir():
                if f.suffix.lower() in exts:
                    return f
    return None


def mix_audio(narration: Path, total_duration: float) -> Path:
    """Mix narration + optional music bed with ducking. Returns mixed WAV."""
    out = RUN_DIR / "09_audio_mix.wav"
    music = find_music_bed()

    if music:
        print(f"  [AUDIO] Mixing narration with music bed: {music.name}")
        # Music: loop to duration, duck to -24dB (0.063x) overall, with voice full
        # EBU R128: target -14 LUFS
        cmd = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-i", str(narration),
            "-stream_loop", "-1", "-i", str(music),
            "-filter_complex", (
                # Voice chain: normalize, compress, full gain
                "[0:a]loudnorm=I=-14:TP=-1:LRA=7,acompressor=threshold=0.05:ratio=4:attack=5:release=50[voice];"
                # Music bed: loop trim, duck heavily
                f"[1:a]atrim=0:{total_duration},asetpts=PTS-STARTPTS,volume=0.16,afade=t=in:st=0:d=1.5[music];"
                # Sidechain duck: voice presence → music ducks -24dB
                "[voice][music]amix=inputs=2:duration=first:weights=1 0.25[out]"
            ),
            "-map", "[out]",
            "-ac", "2", "-ar", "48000",
            "-c:a", "pcm_s16le",
            str(out)
        ]
    else:
        print("  [AUDIO] No music bed found. Using narration only with loudnorm.")
        cmd = [
            "ffmpeg", "-y", "-loglevel", "warning",
            "-i", str(narration),
            "-af", "loudnorm=I=-14:TP=-1:LRA=7",
            "-ac", "2", "-ar", "48000",
            "-c:a", "pcm_s16le",
            str(out)
        ]

    subprocess.run(cmd, check=True)
    return out


# ── Main pipeline ──────────────────────────────────────────────────────────────
def main():
    print("=" * 64)
    print(" ENGLAND REMASTERED — v2 Render Pipeline")
    print("=" * 64)

    # Load timing data
    timings_raw = json.loads(TIMINGS.read_text(encoding="utf-8"))
    words_all   = json.loads(WORDS_JSON.read_text(encoding="utf-8"))

    total_duration = max(t["end"] for t in timings_raw.values())
    print(f"Total duration: {total_duration:.2f}s | Scenes: {len(SCENES)}")

    # ── Phase 1: Render all scene clips ────────────────────────────────────────
    print("\n[PHASE 1] Rendering scene clips...")
    scene_clip_paths = []
    for scene_id, scene in SCENES.items():
        timings = timings_raw[scene_id]
        clip = render_scene(scene_id, scene, timings, words_all)
        scene_clip_paths.append(clip)

    # ── Phase 2: Concatenate all clips ────────────────────────────────────────
    print("\n[PHASE 2] Concatenating clips...")
    concat_list = CLIPS_DIR / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in scene_clip_paths:
            f.write(f"file '{clip.as_posix()}'\n")

    raw_video = RUN_DIR / "09_raw_video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(raw_video)
    ], check=True)
    print(f"  [OK] Raw video: {raw_video.name}")

    # ── Phase 3: Mix audio ─────────────────────────────────────────────────────
    print("\n[PHASE 3] Mixing audio...")
    mixed_audio = mix_audio(NARRATION, total_duration)
    print(f"  [OK] Mixed audio: {mixed_audio.name}")

    # ── Phase 4: Mux video + audio ────────────────────────────────────────────
    print("\n[PHASE 4] Muxing video + audio...")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(raw_video),
        "-i", str(mixed_audio),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(FINAL_OUT)
    ], check=True)

    size_mb = FINAL_OUT.stat().st_size / 1_048_576
    print(f"\n{'=' * 64}")
    print(f"[DONE] FINAL OUTPUT: {FINAL_OUT}")
    print(f"   Size: {size_mb:.1f} MB | Duration: {total_duration:.2f}s")
    print(f"{'=' * 64}")


if __name__ == "__main__":
    main()
