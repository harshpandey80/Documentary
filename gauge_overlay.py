"""
gauge_overlay.py - deterministic vertical dimension/depth gauge animation with human anchor.
Follows the exact Phase 8 countup_overlay.py architecture. No LLM, no AI, no API key.

Renders a short TRANSPARENT overlay clip: an animated vertical measuring gauge with
hash marks, level fluid rise, numerical readout, and a hand-checked sourced human anchor.

Usage:
    python gauge_overlay.py 10000 "METERS" "OCEAN TRENCH" gauge.webm
    python gauge_overlay.py 330 "METERS" "EIFFEL TOWER HEIGHT" out.webm --dur 3.5 --count 1.8

Requires: Pillow, numpy (optional), and ffmpeg on PATH.
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
SS = 2  # supersampling factor: draw at 2x, shrink for smooth edges

# Style tokens
STYLE = {
    "panel": (6, 12, 20, 165),      # RGBA, dark translucent panel
    "number": (255, 255, 255, 255),
    "label": (170, 205, 230, 255),
    "rail": (30, 45, 65, 220),       # Gauge rail background
    "accent": (0, 216, 255, 255),    # Cyan telemetry accent
    "anchor": (255, 176, 46, 255),   # Warm Amber anchor badge
}

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",      # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]

# Sourced human anchor library
ANCHORS = [
    ("Human Height", 1.8, "Standard anthropometry (6 ft)"),
    ("Blue Whale Length", 30.0, "NOAA Fisheries"),
    ("Boeing 747 Length", 70.6, "Boeing Specifications"),
    ("Statue of Liberty", 93.0, "National Park Service"),
    ("Eiffel Tower", 330.0, "SETE Paris Official Architecture"),
    ("Burj Khalifa", 828.0, "Emaar Engineering"),
    ("Mount Everest Peak", 8848.0, "Survey of Nepal / China 2020"),
    ("Cruising Altitude", 10668.0, "FAA FL350 (35,000 ft)"),
    ("Mariana Trench Abyssal Plain", 10984.0, "NOAA / UNH Bathymetry (36,037 ft)"),
]


def load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def clamp(x):
    return max(0.0, min(1.0, x))


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 3 * x * x - 2 * x * x * x


def find_nearest_anchor(meters):
    best_anchor, best_dist = None, float("inf")
    for name, val, src in ANCHORS:
        dist = abs(math.log10(max(1.0, meters)) - math.log10(val))
        if dist < best_dist:
            best_dist, best_anchor = dist, (name, val, src)
    return best_anchor


def draw_frame(t, value, unit, label, dur, count_time, fade, width=W, height=H):
    """Return one RGBA frame (width x height) for time t seconds. Pure function of t."""
    canvas = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    a_in = ease_in_out(clamp(t / fade))
    a_out = ease_in_out(clamp((dur - t) / fade))
    alpha = min(a_in, a_out)

    slide = int((1 - ease_out_cubic(clamp(t / (fade * 1.5)))) * 40 * SS)

    progress = ease_out_cubic(clamp(t / count_time))
    current_val = value * progress
    num_str = f"{int(round(current_val)):,}" if value >= 10 else f"{current_val:.1f}"

    base_scale = min(width, height) / 1080.0
    f_num = load_font(int(140 * SS * base_scale))
    f_unit = load_font(int(54 * SS * base_scale))
    f_label = load_font(int(44 * SS * base_scale))
    f_anc = load_font(int(30 * SS * base_scale))

    panel_w = int(1080 * SS * base_scale)
    panel_h = int(540 * SS * base_scale)
    cx, cy = (width * SS) // 2, (height * SS) // 2 + slide
    x0, y0 = cx - panel_w // 2, cy - panel_h // 2

    d.rounded_rectangle([x0, y0, x0 + panel_w, y0 + panel_h], radius=int(36 * SS * base_scale), fill=STYLE["panel"])

    # Gauge Rail on the left
    gx = x0 + int(70 * SS * base_scale)
    gy0 = y0 + int(70 * SS * base_scale)
    gh = int(320 * SS * base_scale)
    gw = int(28 * SS * base_scale)
    gy1 = gy0 + gh

    # Background rail
    d.rounded_rectangle([gx, gy0, gx + gw, gy1], radius=int(14 * SS * base_scale), fill=STYLE["rail"])

    # Fluid fill rising
    fill_h = int(gh * progress)
    d.rounded_rectangle([gx, gy1 - fill_h, gx + gw, gy1], radius=int(14 * SS * base_scale), fill=STYLE["accent"])

    # Hash tick marks
    for i in range(6):
        ty = gy0 + int(gh * (i / 5.0))
        d.line([(gx + gw + int(8 * SS * base_scale), ty), (gx + gw + int(24 * SS * base_scale), ty)],
               fill=(70, 100, 135), width=int(3 * SS * base_scale))

    # Right side: Number and Unit
    rx = gx + gw + int(60 * SS * base_scale)
    nb = d.textbbox((0, 0), num_str, font=f_num)
    d.text((rx - nb[0], y0 + int(80 * SS * base_scale) - nb[1]), num_str, font=f_num, fill=STYLE["number"])
    d.text((rx + (nb[2] - nb[0]) + int(24 * SS * base_scale), y0 + int(140 * SS * base_scale)),
           unit.upper(), font=f_unit, fill=STYLE["accent"])

    # Label
    if label:
        d.text((rx, y0 + int(240 * SS * base_scale)), label.upper(), font=f_label, fill=STYLE["label"])

    # Sourced Human Anchor comparison
    anchor_info = find_nearest_anchor(value if "m" in unit.lower() else value * 0.3048)
    if anchor_info:
        anc_name, anc_val, anc_src = anchor_info
        ratio = value / max(1.0, anc_val if "m" in unit.lower() else anc_val / 0.3048)
        comp_box_y = y0 + int(420 * SS * base_scale)
        d.rounded_rectangle([rx, comp_box_y, x0 + panel_w - int(50 * SS * base_scale), comp_box_y + int(80 * SS * base_scale)],
                            radius=int(12 * SS * base_scale), fill=(16, 26, 42, 220))
        d.text((rx + int(24 * SS * base_scale), comp_box_y + int(16 * SS * base_scale)),
               f"SCALE REFERENCE: {ratio:.1f}x {anc_name.upper()} ({anc_src})", font=f_anc, fill=STYLE["anchor"])

    if alpha < 1.0:
        r, g, b, a = canvas.split()
        a = a.point(lambda p: int(p * alpha))
        canvas = Image.merge("RGBA", (r, g, b, a))
    return canvas.resize((width, height), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("value", type=float)
    ap.add_argument("unit", default="METERS")
    ap.add_argument("label")
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=3.0, help="total clip length in seconds")
    ap.add_argument("--count", type=float, default=1.6, help="seconds until the gauge lands on value")
    ap.add_argument("--fade", type=float, default=0.3)
    ap.add_argument("--width", type=int, default=W)
    ap.add_argument("--height", type=int, default=H)
    ap.add_argument("--fps", type=int, default=FPS)
    args = ap.parse_args()

    width, height, fps = args.width, args.height, args.fps
    n_frames = int(round(args.dur * fps))

    out_lower = args.out.lower()
    if out_lower.endswith(".webm"):
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "28",
            args.out,
        ]
    elif out_lower.endswith(".mov"):
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
            "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
            args.out,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "20",
            args.out,
        ]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n_frames):
        frame = draw_frame(i / fps, args.value, args.unit, args.label, args.dur, args.count, args.fade, width, height)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")

    print(f"Wrote {args.out} ({n_frames} frames)")
    print(f"Composite with:")
    print(
        f'ffmpeg -i video.mp4 -c:v libvpx-vp9 -i {args.out} -filter_complex '
        f'"[1]setpts=PTS+12.4/TB[o];[0][o]overlay=eof_action=pass" -c:a copy out.mp4'
    )


if __name__ == "__main__":
    main()
