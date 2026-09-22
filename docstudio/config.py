import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR / "workspace"
RUNS_DIR = WORKSPACE_DIR / "runs"
ASSETS_DIR = BASE_DIR / "assets"
SFX_DIR = ASSETS_DIR / "sfx"
FONTS_DIR = ASSETS_DIR / "fonts"
BROLL_DIR = ASSETS_DIR / "broll_videos"
MUSIC_DIR = ASSETS_DIR / "music"

# Ensure required directories exist
for directory in [WORKSPACE_DIR, RUNS_DIR, ASSETS_DIR, SFX_DIR, FONTS_DIR, BROLL_DIR, MUSIC_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

# LLM Configuration
# Priority: 1. Gemini, 2. Groq, 3. OpenRouter
DOCSTUDIO_LLM_PROVIDER = os.getenv(
    "DOCSTUDIO_LLM_PROVIDER",
    "gemini" if GEMINI_API_KEY else ("groq" if GROQ_API_KEY else ("openrouter" if OPENROUTER_API_KEY else "fallback"))
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")
DOCSTUDIO_MODEL = os.getenv("DOCSTUDIO_MODEL", GEMINI_MODEL if GEMINI_API_KEY else (GROQ_MODEL if GROQ_API_KEY else OPENROUTER_MODEL))

# Video Specs & Aspect Ratios
ASPECT_RATIOS = {
    "16:9": {"width": 1920, "height": 1080, "name": "YouTube Documentary (16:9)"},
    "9:16": {"width": 1080, "height": 1920, "name": "TikTok / Shorts / Reels (9:16)"},
}

DEFAULT_ASPECT_RATIO = os.getenv("DOCSTUDIO_ASPECT_RATIO", "16:9")
if DEFAULT_ASPECT_RATIO not in ASPECT_RATIOS:
    DEFAULT_ASPECT_RATIO = "16:9"

DEFAULT_WIDTH = ASPECT_RATIOS[DEFAULT_ASPECT_RATIO]["width"]
DEFAULT_HEIGHT = ASPECT_RATIOS[DEFAULT_ASPECT_RATIO]["height"]
DEFAULT_FPS = 30
MAX_SHOT_DURATION_SECONDS = 5.0
MIN_SHOT_DURATION_SECONDS = 2.0
DEAD_AIR_THRESHOLD_SECONDS = 1.5

# Narration / TTS Defaults
DOCSTUDIO_TTS_ENGINE = os.getenv("DOCSTUDIO_TTS_ENGINE", "voxcpm")
VOXCPM_API_URL = os.getenv("VOXCPM_API_URL", "")
VOXCPM_MODEL_ID = os.getenv("VOXCPM_MODEL_ID", "openbmb/VoxCPM2")
VOXCPM_VOICE_PROMPT = os.getenv(
    "VOXCPM_VOICE_PROMPT",
    "(A solemn, authoritative male investigative documentary narrator with deep resonant tone and crisp diction)"
)

DEFAULT_VOICE = os.getenv("DOCSTUDIO_VOICE", "en-US-ChristopherNeural")
DEFAULT_VOICE_RATE = os.getenv("DOCSTUDIO_VOICE_RATE", "+25%")
DEFAULT_VOICE_PITCH = "+0Hz"

# Supported documentary voices
VOICE_PROFILES = {
    "christopher": "en-US-ChristopherNeural",   # Deep, investigative, true crime
    "ryan": "en-GB-RyanNeural",                 # British BBC documentary style
    "guy": "en-US-GuyNeural",                   # Engaging modern history
    "eric": "en-US-EricNeural",                 # Authoritative disaster analysis
    "sonia": "en-GB-SoniaNeural",               # Elegant historical narration
}

# Subtitle / Caption Presets
DEFAULT_CAPTION_STYLE = os.getenv("DOCSTUDIO_CAPTION_STYLE", "documentary")

CAPTION_STYLES = {
    "cinematic": {
        "font_name": "Georgia",
        "font_size": 46,
        "primary_color": "&H00F5F5F5",      # Warm Crisp White
        "secondary_color": "&H0000D7FF",    # Amber/Gold Active Word
        "outline_color": "&H00101010",      # Soft Deep Charcoal
        "back_color": "&H60000000",
        "outline_width": 2,
        "shadow_offset": 2,
        "alignment": 2,                     # Bottom Center
        "margin_v": 75,
        "words_per_line": 5,
        "uppercase": False,
    },
    "editorial": {
        "font_name": "Inter",
        "font_size": 44,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00E0E000",    # Cyan Active Pop
        "outline_color": "&H00181818",
        "back_color": "&H80000000",
        "outline_width": 3,
        "shadow_offset": 1,
        "alignment": 2,
        "margin_v": 70,
        "words_per_line": 5,
        "uppercase": False,
    },
    "investigative": {
        "font_name": "Courier New",
        "font_size": 42,
        "primary_color": "&H00D0D0D0",      # Declassified type tone
        "secondary_color": "&H0000E5FF",    # Amber forensic highlight
        "outline_color": "&H00050505",
        "back_color": "&H90000000",
        "outline_width": 3,
        "shadow_offset": 2,
        "alignment": 2,
        "margin_v": 80,
        "words_per_line": 4,
        "uppercase": True,
    },
    "minimal": {
        "font_name": "Arial",
        "font_size": 40,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H00FFFFFF",    # Pure non-distracting white
        "outline_color": "&H00202020",
        "back_color": "&H00000000",
        "outline_width": 2,
        "shadow_offset": 2,
        "alignment": 2,
        "margin_v": 65,
        "words_per_line": 6,
        "uppercase": False,
    },
    "kinetic": {
        "font_name": "Montserrat",
        "font_size": 52,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000FF00",    # Neon green pop
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "outline_width": 4,
        "shadow_offset": 3,
        "alignment": 2,
        "margin_v": 90,
        "words_per_line": 3,
        "uppercase": True,
    },
    "shorts": {
        "font_name": "Impact",
        "font_size": 68,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0000FF00",
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "outline_width": 5,
        "shadow_offset": 4,
        "alignment": 2,
        "margin_v": 380,                    # Safe zone padding
        "words_per_line": 3,
        "uppercase": True,
    },
    "documentary": {
        "font_name": "Arial",
        "font_size": 48,
        "primary_color": "&H00FFFFFF",      # Crisp White (BBGGRR)
        "secondary_color": "&H002BF7F7",    # Golden / Amber active word
        "outline_color": "&H000A0A0A",      # Dark Charcoal Outline
        "back_color": "&H80000000",         # Semi-transparent backing
        "outline_width": 3,
        "shadow_offset": 2,
        "alignment": 2,                     # Bottom Center
        "margin_v": 60,
        "words_per_line": 5,
        "uppercase": False,
    },
    "hormozi": {
        "font_name": "Impact",
        "font_size": 68,
        "primary_color": "&H00FFFFFF",      # White
        "secondary_color": "&H0000FF00",    # Neon Green active word
        "outline_color": "&H00000000",      # Solid Black Outline
        "back_color": "&H00000000",
        "outline_width": 5,
        "shadow_offset": 4,
        "alignment": 2,                     # Lower Third / Bottom Center with Shorts safe zone
        "margin_v": 380,
        "words_per_line": 3,
        "uppercase": True,
    },
    "mrbeast": {
        "font_name": "Arial Black",
        "font_size": 64,
        "primary_color": "&H0000FFFF",      # Vivid Yellow
        "secondary_color": "&H00FF3300",    # Vivid Red/Cyan pop
        "outline_color": "&H00000000",      # Thick Black
        "back_color": "&H00000000",
        "outline_width": 6,
        "shadow_offset": 3,
        "alignment": 2,                     # Bottom Center
        "margin_v": 90,
        "words_per_line": 4,
        "uppercase": True,
    }
}

# Audio Mixing Defaults (Narration voice is strictly dominant over background music and SFX)
VOICE_TARGET_LUFS = -14.0       # Standard broadcast/YouTube streaming loudness
VOICE_GAIN = float(os.getenv("DOCSTUDIO_VOICE_GAIN", "1.00"))           # Full vocal punch and clarity
MUSIC_NORMAL_VOLUME = float(os.getenv("DOCSTUDIO_MUSIC_GAIN", "0.16"))   # Background music when voice is silent
DUCKING_ATTENUATION_DB = float(os.getenv("DOCSTUDIO_DUCKING_DB", "-24.0")) # Deep ducking during voiceover (-24dB)
DUCK_DEPTH = 10 ** (DUCKING_ATTENUATION_DB / 20.0)                      # ~0.063 linear duck depth
SFX_VOLUME = float(os.getenv("DOCSTUDIO_SFX_GAIN", "0.22"))             # Subtle accent SFX (never competes with voice)
ROOM_TONE_VOLUME = float(os.getenv("DOCSTUDIO_ROOM_TONE_GAIN", "0.18")) # Subtle warm tape tone

