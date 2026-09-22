"""
Documentary Audio Library Setup Script
Indexes and installs CC0 sound effects & real background music tracks into assets/sfx/ and assets/music/.
"""

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
SFX_DIR = ASSETS_DIR / "sfx"
MUSIC_DIR = ASSETS_DIR / "music"
SCRATCH_DIR = BASE_DIR / "scratch"
AUDIO_REPOS_DIR = SCRATCH_DIR / "audio_repos"

def install_music():
    """Installs real ambient and cinematic documentary music beds into assets/music/."""
    print("[1/3] Installing real documentary background music tracks into assets/music/...")
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    
    ambient_dir = AUDIO_REPOS_DIR / "lavender_sounds" / "Maximiliano-Stradex-Ambient"
    if ambient_dir.exists():
        music_map = {
            "tension.mp3": ambient_dir / "Theme_1.mp3",
            "somber.mp3": ambient_dir / "Ambient_1.mp3",
            "ambient_drone.mp3": ambient_dir / "Ambient_2.mp3",
            "investigative.mp3": ambient_dir / "Theme_1.mp3",
            "documentary.mp3": ambient_dir / "Ambient_1.mp3",
        }
        for target_name, src_file in music_map.items():
            if src_file.exists():
                dest = MUSIC_DIR / target_name
                shutil.copy2(src_file, dest)
                print(f"  -> Music installed: {target_name} ({dest.stat().st_size / (1024*1024):.2f} MB)")
    else:
        print("  Notice: ambient music source folder not found.")

def install_sfx():
    """Installs high-impact documentary foley and cinematic SFX into assets/sfx/."""
    print("\n[2/3] Installing real documentary sound effects into assets/sfx/...")
    SFX_DIR.mkdir(parents=True, exist_ok=True)

    lavender = AUDIO_REPOS_DIR / "lavender_sounds"
    uisfx = AUDIO_REPOS_DIR / "uisfx"
    kenney = SCRATCH_DIR / "kenney_sounds"

    # Search for best audio matches across repositories
    all_audio_files = []
    for r in [lavender, uisfx, kenney]:
        if r.exists():
            all_audio_files.extend(list(r.glob("**/*.wav")) + list(r.glob("**/*.mp3")) + list(r.glob("**/*.flac")))

    print(f"  Indexed {len(all_audio_files)} audio samples across local repositories.")

    # Target documentary sound effects mapping
    targets = {
        "whoosh.wav": ["switch", "whoosh", "swoosh", "swipe", "slide"],
        "impact_hit.wav": ["impact", "hit", "punch", "thud", "pluck"],
        "sub_impact.wav": ["bass", "sub", "low", "deep", "boom"],
        "deep_braam.wav": ["braam", "horn", "swell", "maximize", "brass"],
        "riser.wav": ["riser", "rise", "swell", "up", "question"],
        "paper_rustle.wav": ["paper", "page", "book"],
        "camera_shutter.wav": ["camera", "click", "shutter"],
        "typing.wav": ["keyboard", "typing", "typewriter"],
        "clock_tick.wav": ["tick", "clock", "watch"],
    }

    installed = 0
    for target_name, keywords in targets.items():
        chosen = None
        for kw in keywords:
            matches = [f for f in all_audio_files if kw in f.stem.lower()]
            if matches:
                chosen = matches[0]
                break

        if chosen:
            dest_file = SFX_DIR / target_name
            shutil.copy2(chosen, dest_file)
            print(f"  -> Installed SFX: {target_name} (from {chosen.name})")
            installed += 1

    print(f"Successfully configured {installed} core documentary sound effects in assets/sfx/.")

def report_status():
    """Reports final audio catalog status."""
    print("\n[3/3] Audio Library Status:")
    sfx_files = list(SFX_DIR.glob("*.*"))
    music_files = list(MUSIC_DIR.glob("*.*"))

    print(f"  assets/sfx/:   {len(sfx_files)} active sound effects ready.")
    for f in sfx_files:
        print(f"    - {f.name} ({f.stat().st_size / 1024:.1f} KB)")

    print(f"\n  assets/music/: {len(music_files)} active background music tracks ready.")
    for f in music_files:
        print(f"    - {f.name} ({f.stat().st_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    install_music()
    install_sfx()
    report_status()
