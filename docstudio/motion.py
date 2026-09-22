from docstudio.config import DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS

# Unified documentary color grading & film texture filter
UNIFIED_COLOR_GRADE_FILTER = (
    "eq=contrast=1.06:brightness=-0.02:saturation=0.85,"
    "colorbalance=rs=0.03:gs=0.01:bs=-0.03:rm=-0.02:gm=0.01:bm=0.03,"
    "noise=alls=11:allf=t+u,"
    "vignette=PI/4.5"
)

def get_ken_burns_filter(
    motion_type: str,
    duration: float,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    fps: int = DEFAULT_FPS,
) -> str:
    """
    Constructs an FFmpeg video filter string combining:
    1. Smooth Ken Burns pan/zoom motion
    2. Universal cinematic documentary color grade & 35mm film grain texture
    Ensures visual cohesion across archival photos, modern stock, and AI art.
    """
    total_frames = max(int(duration * fps), 1)

    scale_filter = f"scale={width*2}:{height*2}:force_original_aspect_ratio=increase,crop={width*2}:{height*2}"
    if motion_type == "zoom_in":
        z_step = 0.15 / total_frames
        kb = (
            f"{scale_filter},"
            f"zoompan=z='min(1.0+{z_step}*on,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )
    elif motion_type == "zoom_out":
        z_step = 0.16 / total_frames
        kb = (
            f"{scale_filter},"
            f"zoompan=z='max(1.18-{z_step}*on,1.02)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )
    elif motion_type == "pan_left":
        kb = (
            f"{scale_filter},"
            f"zoompan=z='1.15':x='(1-(on/{total_frames}))*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )
    elif motion_type == "pan_right":
        kb = (
            f"{scale_filter},"
            f"zoompan=z='1.15':x='(on/{total_frames})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )
    elif motion_type == "zoom_punch":
        kb = (
            f"{scale_filter},"
            f"zoompan=z='1.10+0.15*exp(-on/15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )
    else:  # subtle_drift
        z_step = 0.06 / total_frames
        kb = (
            f"{scale_filter},"
            f"zoompan=z='min(1.02+{z_step}*on,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )

    # Chain Ken Burns with the unified color grade & film texture
    return f"{kb},{UNIFIED_COLOR_GRADE_FILTER}"
