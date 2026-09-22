"""
dotgrid_overlay.py - deterministic "1 in N" incidence dot-grid animation.
Follows the exact Phase 8 countup_overlay.py architecture. No LLM, no AI, no API key.

Renders a short TRANSPARENT overlay clip: an animated matrix of dots where neutral items
are dimmed slate and the target fraction (1 in N) illuminates in vivid pulsing accent.

Usage:
    python dotgrid_overlay.py 5 "PEOPLE" "IMPERIAL SUBJECTS" dotgrid.webm
    python dotgrid_overlay.py 20 "SOLDIERS" "SURVIVAL ODDS" out.webm --dur 3.5 --count 1.6

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
    "dot_neutral": (35, 48, 68, 220),
    "accent": (255, 68, 68, 255),    # High-contrast red/coral pulse
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


def draw_frame(t, ratio_n, unit, label, dur, count_time, fade, width=W, height=H):
    """Return one RGBA frame (width x height) for time t seconds. Pure function of t."""
    canvas = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    a_in = ease_in_out(clamp(t / fade))
    a_out = ease_in_out(clamp((dur - t) / fade))
    alpha = min(a_in, a_out)

    slide = int((1 - ease_out_cubic(clamp(t / (fade * 1.5)))) * 40 * SS)
    progress = ease_out_cubic(clamp(t / count_time))

    base_scale = min(width, height) / 1080.0
    f_num = load_font(int(140 * SS * base_scale))
    f_label = load_font(int(46 * SS * base_scale))

    header_text = f"1 IN {int(ratio_n)}"
    if unit:
        header_text = f"{header_text} {unit.upper()}"

    panel_w = int(980 * SS * base_scale)
    panel_h = int(520 * SS * base_scale)
    cx, cy = (width * SS) // 2, (height * SS) // 2 + slide
    x0, y0 = cx - panel_w // 2, cy - panel_h // 2

    d.rounded_rectangle([x0, y0, x0 + panel_w, y0 + panel_h], radius=int(36 * SS * base_scale), fill=STYLE["panel"])

    # Header title
    nb = d.textbbox((0, 0), header_text, font=f_num)
    d.text((cx - (nb[2] - nb[0]) // 2 - nb[0], y0 + int(40 * SS * base_scale) - nb[1]),
           header_text, font=f_num, fill=STYLE["number"])

    # Matrix of dots
    n_display = min(50, max(10, int(ratio_n)))
    cols = 10
    rows = math.ceil(n_display / cols)
    cell_size = int(50 * SS * base_scale)
    grid_w = cols * cell_size
    gx0 = cx - grid_w // 2
    gy0 = y0 + int(210 * SS * base_scale)
    dot_r = int(14 * SS * base_scale)

    for i in range(n_display):
        c = i % cols
        r = i // cols
        dcx = gx0 + c * cell_size + cell_size // 2
        dcy = gy0 + r * cell_size + cell_size // 2

        if i == 0:
            # Active illuminated dot
            pulse_r = int(dot_r * (1.0 + 0.35 * (1.0 - progress)))
            d.ellipse([dcx - pulse_r, dcy - pulse_r, dcx + pulse_r, dcy + pulse_r],
                      fill=STYLE["accent"], outline=(255, 255, 255), width=int(2 * SS * base_scale))
        else:
            d.ellipse([dcx - dot_r, dcy - dot_r, dcx + dot_r, dcy + dot_r], fill=STYLE["dot_neutral"])

    # Label
    if label:
        lb = d.textbbox((0, 0), label, font=f_label)
        d.text((cx - (lb[2] - lb[0]) // 2 - lb[0], y0 + panel_h - int(65 * SS * base_scale) - lb[1]),
               label.upper(), font=f_label, fill=STYLE["label"])

    if alpha < 1.0:
        r, g, b, a = canvas.split()
        a = a.point(lambda p: int(p * alpha))
        canvas = Image.merge("RGBA", (r, g, b, a))
    return canvas.resize((width, height), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("value", type=float, help="denominator in 1 in N (e.g. 5 for 1 in 5)")
    ap.add_argument("unit", default="")
    ap.add_argument("label")
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=3.0, help="total clip length in seconds")
    ap.add_argument("--count", type=float, default=1.6, help="seconds until the dot grid illuminates")
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
