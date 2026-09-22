"""
comparison_overlay.py - deterministic "N times" / "than" comparative visualizer.
Follows the exact Phase 8 countup_overlay.py architecture. No LLM, no AI, no API key.

Renders a short TRANSPARENT overlay clip: dual comparative horizontal bars contrasting
a baseline against a target with an animated multiplier badge and ratio label.

Usage:
    python comparison_overlay.py 5.0 "TIMES" "FORCE MULTIPLIER" comparison.webm
    python comparison_overlay.py 3.5 "x" "EXPLOSIVE YIELD" out.webm --baseline "STANDARD YIELD" --target "THERMONUCLEAR"

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
    "base_bar": (40, 56, 78, 220),   # Baseline bar color
    "accent": (0, 240, 160, 255),    # Neon Emerald target bar
    "gold": (255, 176, 46, 255),     # Multiplier badge
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


def draw_frame(t, multiplier, unit, label, dur, count_time, fade, width=W, height=H, baseline="BASELINE", target="TARGET"):
    """Return one RGBA frame (width x height) for time t seconds. Pure function of t."""
    canvas = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # Global opacity: fade in, hold, fade out
    a_in = ease_in_out(clamp(t / fade))
    a_out = ease_in_out(clamp((dur - t) / fade))
    alpha = min(a_in, a_out)

    # Slide up slightly while fading in
    slide = int((1 - ease_out_cubic(clamp(t / (fade * 1.5)))) * 40 * SS)

    # Easing for multiplier count
    progress = ease_out_cubic(clamp(t / count_time))
    current_mult = 1.0 + (multiplier - 1.0) * progress

    mult_text = f"{current_mult:.1f}x" if multiplier != int(multiplier) else f"{int(round(current_mult))}x"
    if unit and unit != "x":
        mult_text = f"{mult_text} {unit.upper()}"

    base_scale = min(width, height) / 1080.0
    f_num = load_font(int(140 * SS * base_scale))
    f_label = load_font(int(46 * SS * base_scale))
    f_bar = load_font(int(34 * SS * base_scale))

    panel_w = int(1120 * SS * base_scale)
    panel_h = int(520 * SS * base_scale)
    cx, cy = (width * SS) // 2, (height * SS) // 2 + slide
    x0, y0 = cx - panel_w // 2, cy - panel_h // 2

    d.rounded_rectangle([x0, y0, x0 + panel_w, y0 + panel_h], radius=int(36 * SS * base_scale), fill=STYLE["panel"])

    # Big multiplier header
    nb = d.textbbox((0, 0), mult_text, font=f_num)
    d.text((cx - (nb[2] - nb[0]) // 2 - nb[0], y0 + int(36 * SS * base_scale) - nb[1]),
           mult_text, font=f_num, fill=STYLE["accent"])

    # Label underneath number
    lb = d.textbbox((0, 0), label, font=f_label)
    d.text((cx - (lb[2] - lb[0]) // 2 - lb[0], y0 + int(185 * SS * base_scale) - lb[1]),
           label.upper(), font=f_label, fill=STYLE["label"])

    # Dual Comparative Bars
    bar_pad = int(80 * SS * base_scale)
    bar_x0 = x0 + bar_pad
    bar_max_w = panel_w - bar_pad * 2

    # Baseline bar (1.0x scale)
    base_ratio = 1.0 / max(1.5, multiplier)
    b1_w = int(bar_max_w * base_ratio)
    b1_y = y0 + int(270 * SS * base_scale)
    b_h = int(48 * SS * base_scale)

    d.rounded_rectangle([bar_x0, b1_y, bar_x0 + b1_w, b1_y + b_h], radius=int(10 * SS * base_scale), fill=STYLE["base_bar"])
    d.text((bar_x0 + int(24 * SS * base_scale), b1_y + int(10 * SS * base_scale)),
           f"1.0x  {baseline.upper()}", font=f_bar, fill=(200, 215, 235))

    # Target bar (expands with progress to full target width)
    target_full_w = bar_max_w
    target_curr_w = int(b1_w + (target_full_w - b1_w) * progress)
    b2_y = y0 + int(350 * SS * base_scale)

    d.rounded_rectangle([bar_x0, b2_y, bar_x0 + target_curr_w, b2_y + b_h], radius=int(10 * SS * base_scale), fill=STYLE["accent"])
    d.text((bar_x0 + int(24 * SS * base_scale), b2_y + int(10 * SS * base_scale)),
           f"{mult_text}  {target.upper()}", font=f_bar, fill=(8, 20, 16))

    # Apply global opacity
    if alpha < 1.0:
        r, g, b, a = canvas.split()
        a = a.point(lambda p: int(p * alpha))
        canvas = Image.merge("RGBA", (r, g, b, a))
    return canvas.resize((width, height), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("value", type=float, help="multiplier value (e.g. 5.0, 3.5)")
    ap.add_argument("unit", default="x")
    ap.add_argument("label")
    ap.add_argument("out")
    ap.add_argument("--baseline", default="BASELINE")
    ap.add_argument("--target", default="TARGET RECORD")
    ap.add_argument("--dur", type=float, default=3.0, help="total clip length in seconds")
    ap.add_argument("--count", type=float, default=1.6, help="seconds until the comparison lands on multiplier")
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
        frame = draw_frame(i / fps, args.value, args.unit, args.label, args.dur, args.count, args.fade,
                           width, height, args.baseline, args.target)
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
