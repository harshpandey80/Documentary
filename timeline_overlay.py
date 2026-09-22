"""
timeline_overlay.py - deterministic historical year timeline animation.
Follows the exact Phase 8 countup_overlay.py architecture. No LLM, no AI, no API key.

Renders a short TRANSPARENT overlay clip: an animated historical era timeline with
eased year counting, an animated cursor landing on the target year, and historical label.

Usage:
    python timeline_overlay.py 1066 "AD" "BATTLE OF HASTINGS" timeline.webm
    python timeline_overlay.py 1945 "YEAR" "END OF WORLD WAR II" out.webm --dur 3.5 --count 1.8

Requires: Pillow, numpy (optional), and ffmpeg on PATH.
"""
import argparse
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
    "track": (40, 56, 78, 220),     # Background timeline track
    "accent": (255, 176, 46, 255),   # Warm Amber accent
}

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",      # Windows
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
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


def draw_frame(t, target_year, unit, label, dur, count_time, fade, width=W, height=H, start_year=None, end_year=None):
    """Return one RGBA frame (width x height) for time t seconds. Pure function of t."""
    canvas = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # Global opacity: fade in, hold, fade out
    a_in = ease_in_out(clamp(t / fade))
    a_out = ease_in_out(clamp((dur - t) / fade))
    alpha = min(a_in, a_out)

    # Slide up slightly while fading in
    slide = int((1 - ease_out_cubic(clamp(t / (fade * 1.5)))) * 40 * SS)

    # Easing for year progress
    progress = ease_out_cubic(clamp(t / count_time))
    s_yr = start_year if start_year is not None else int(target_year - 200)
    e_yr = end_year if end_year is not None else int(target_year + 100)

    current_yr = int(round(s_yr + (target_year - s_yr) * progress))
    year_text = f"{current_yr}"
    if unit:
        year_text = f"{year_text} {unit.upper()}"

    base_scale = min(width, height) / 1080.0
    f_num = load_font(int(170 * SS * base_scale))
    f_label = load_font(int(50 * SS * base_scale))
    f_tick = load_font(int(30 * SS * base_scale))

    # Panel sizing
    panel_w = int(1080 * SS * base_scale)
    panel_h = int(480 * SS * base_scale)
    cx, cy = (width * SS) // 2, (height * SS) // 2 + slide
    x0, y0 = cx - panel_w // 2, cy - panel_h // 2

    d.rounded_rectangle([x0, y0, x0 + panel_w, y0 + panel_h], radius=int(36 * SS * base_scale), fill=STYLE["panel"])

    # Giant year text
    nb = d.textbbox((0, 0), year_text, font=f_num)
    d.text((cx - (nb[2] - nb[0]) // 2 - nb[0], y0 + int(40 * SS * base_scale) - nb[1]),
           year_text, font=f_num, fill=STYLE["number"])

    # Timeline track line
    track_y = y0 + int(290 * SS * base_scale)
    track_pad = int(80 * SS * base_scale)
    track_x0, track_x1 = x0 + track_pad, x0 + panel_w - track_pad
    d.line([(track_x0, track_y), (track_x1, track_y)], fill=STYLE["track"], width=int(8 * SS * base_scale))

    # Ticks along the timeline
    total_ticks = 5
    for i in range(total_ticks):
        tx = track_x0 + int((track_x1 - track_x0) * (i / (total_ticks - 1)))
        tick_h = int(14 * SS * base_scale)
        d.line([(tx, track_y - tick_h), (tx, track_y + tick_h)], fill=STYLE["track"], width=int(4 * SS * base_scale))

    # Year cursor landing
    norm_target = (target_year - s_yr) / max(1, e_yr - s_yr)
    cursor_x = int(track_x0 + (track_x1 - track_x0) * (norm_target * progress))

    # Active progress line
    d.line([(track_x0, track_y), (cursor_x, track_y)], fill=STYLE["accent"], width=int(8 * SS * base_scale))

    # Glowing beacon marker at cursor
    beacon_r = int(16 * SS * base_scale)
    d.ellipse([cursor_x - beacon_r, track_y - beacon_r, cursor_x + beacon_r, track_y + beacon_r],
              fill=STYLE["accent"], outline=(255, 255, 255), width=int(2 * SS * base_scale))

    # Label underneath
    if label:
        lb = d.textbbox((0, 0), label, font=f_label)
        d.text((cx - (lb[2] - lb[0]) // 2 - lb[0], y0 + int(360 * SS * base_scale) - lb[1]),
               label.upper(), font=f_label, fill=STYLE["label"])

    # Apply global opacity
    if alpha < 1.0:
        r, g, b, a = canvas.split()
        a = a.point(lambda p: int(p * alpha))
        canvas = Image.merge("RGBA", (r, g, b, a))
    return canvas.resize((width, height), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("value", type=int, help="4-digit historical year (e.g. 1066, 1945)")
    ap.add_argument("unit", default="AD")
    ap.add_argument("label")
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=3.0, help="total clip length in seconds")
    ap.add_argument("--count", type=float, default=1.6, help="seconds until the timeline lands on year")
    ap.add_argument("--fade", type=float, default=0.3)
    ap.add_argument("--start", type=int, default=None, help="timeline starting year")
    ap.add_argument("--end", type=int, default=None, help="timeline ending year")
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
        frame = draw_frame(i / fps, args.value, args.unit, args.label, args.dur, args.count, args.fade,
                           width, height, args.start, args.end)
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
