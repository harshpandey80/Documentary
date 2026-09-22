"""
countup_overlay.py - deterministic number animation. No LLM, no AI, no API key.

Renders a short TRANSPARENT overlay clip: a big number that counts up with easing,
a label, and an accent bar, fading in and out. Same input always gives the same output.

Usage:
    python countup_overlay.py 36000 "FEET" "DEEPEST POINT" countup.webm
    python countup_overlay.py 500 "YEARS" "LIFESPAN" out.webm --dur 3.5 --count 1.8

Requires: Pillow, numpy (optional), and ffmpeg on PATH.
Composite onto your video with the ffmpeg command printed at the end.
"""
import argparse
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
SS = 2  # supersampling factor: draw at 2x, shrink for smooth edges

# Style tokens (in a real pipeline these come from project.yaml)
STYLE = {
    "panel": (6, 12, 20, 165),      # RGBA, dark translucent panel
    "number": (255, 255, 255, 255),
    "label": (170, 205, 230, 255),
    "accent": (255, 176, 46, 255),
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


def draw_frame(t, value, unit, label, dur, count_time, fade, width=W, height=H):
    """Return one RGBA frame (width x height) for time t seconds. Pure function of t."""
    canvas = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # Global opacity: fade in, hold, fade out
    a_in = ease_in_out(clamp(t / fade))
    a_out = ease_in_out(clamp((dur - t) / fade))
    alpha = min(a_in, a_out)

    # Slide up slightly while fading in
    slide = int((1 - ease_out_cubic(clamp(t / (fade * 1.5)))) * 40 * SS)

    # Counting value: eased so it lands on the final number exactly
    progress = ease_out_cubic(clamp(t / count_time))
    shown = int(round(value * progress))
    number_text = f"{shown:,}"

    # Responsive font sizing based on canvas scale
    base_scale = min(width, height) / 1080.0
    f_num = load_font(int(230 * SS * base_scale))
    f_unit = load_font(int(80 * SS * base_scale))
    f_label = load_font(int(56 * SS * base_scale))

    # Measure
    nb = d.textbbox((0, 0), number_text, font=f_num)
    ub = d.textbbox((0, 0), unit, font=f_unit) if unit else (0, 0, 0, 0)
    lb = d.textbbox((0, 0), label, font=f_label) if label else (0, 0, 0, 0)
    gap = int(36 * SS * base_scale) if unit else 0
    row_w = (nb[2] - nb[0]) + gap + (ub[2] - ub[0])
    panel_w = max(row_w, lb[2] - lb[0]) + int(140 * SS * base_scale)
    panel_h = int(470 * SS * base_scale)
    cx, cy = (width * SS) // 2, (height * SS) // 2 + slide
    x0, y0 = cx - panel_w // 2, cy - panel_h // 2

    d.rounded_rectangle([x0, y0, x0 + panel_w, y0 + panel_h], radius=int(36 * SS * base_scale), fill=STYLE["panel"])

    # Number + unit on one row
    row_x = cx - row_w // 2
    num_y = y0 + int(40 * SS * base_scale) - nb[1]
    d.text((row_x - nb[0], num_y), number_text, font=f_num, fill=STYLE["number"])
    if unit:
        unit_y = y0 + int(40 * SS * base_scale) + (nb[3] - nb[1]) - (ub[3] - ub[1]) - ub[1]
        d.text((row_x + (nb[2] - nb[0]) + gap - ub[0], unit_y), unit, font=f_unit, fill=STYLE["accent"])

    # Accent bar grows with the count
    bar_y = y0 + int(300 * SS * base_scale)
    bar_full = panel_w - int(140 * SS * base_scale)
    d.rounded_rectangle(
        [cx - bar_full // 2, bar_y, cx - bar_full // 2 + int(bar_full * progress), bar_y + int(10 * SS * base_scale)],
        radius=int(5 * SS * base_scale), fill=STYLE["accent"],
    )

    # Label
    if label:
        d.text((cx - (lb[2] - lb[0]) // 2 - lb[0], bar_y + int(50 * SS * base_scale) - lb[1]), label, font=f_label, fill=STYLE["label"])

    # Apply global opacity to the alpha channel, then downscale
    if alpha < 1.0:
        r, g, b, a = canvas.split()
        a = a.point(lambda p: int(p * alpha))
        canvas = Image.merge("RGBA", (r, g, b, a))
    return canvas.resize((width, height), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("value", type=float)
    ap.add_argument("unit")
    ap.add_argument("label")
    ap.add_argument("out")
    ap.add_argument("--dur", type=float, default=3.0, help="total clip length in seconds")
    ap.add_argument("--count", type=float, default=1.6, help="seconds until the count lands on the value")
    ap.add_argument("--fade", type=float, default=0.3)
    ap.add_argument("--width", type=int, default=W)
    ap.add_argument("--height", type=int, default=H)
    ap.add_argument("--fps", type=int, default=FPS)
    args = ap.parse_args()

    width = args.width
    height = args.height
    fps = args.fps
    n_frames = int(round(args.dur * fps))

    # Support WebM VP9 (with alpha), ProRes 4444 (.mov), or MP4
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

    from pathlib import Path
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
