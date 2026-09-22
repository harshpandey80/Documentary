"""
Phase 5 — TTS Engine Wrapper
------------------------------
Routes synthesis through the active engine (Edge-TTS or VoxCPM2).
Implements the Gate 3 voice lab: generates 3 narrator sample takes
from the first hook sentence so the producer can approve before full render.

VoxCPM2 status on this hardware:
  VoxCPM2 / VoxCPM requires an ONNX runtime with a ~2–4 GB model download.
  On CPU with 4 GB free RAM this is marginal.  The code tries to install
  and run it; if it fails it falls back silently to Edge-TTS.
  The fallback is NOT silent failure — it prints a clear message.

Usage:
    from docstudio.tts_voice_lab import TTSVoiceLab
    lab = TTSVoiceLab()
    takes = lab.generate_takes("Sixty-eight years ago a craft vanished.")
    # Prints paths to 3 WAV files for producer approval
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import List, Tuple

from docstudio.config import DEFAULT_VOICE, DEFAULT_VOICE_RATE, DEFAULT_VOICE_PITCH

# Three distinct voice personas for the producer to choose from
_TAKE_CONFIGS: List[dict] = [
    {"voice": DEFAULT_VOICE, "rate": "+25%", "pitch": "-5Hz",
     "label": "Take A: Default (High-retention +25% speed, -5Hz pitch)"},
    {"voice": DEFAULT_VOICE, "rate": "+20%", "pitch": "+0Hz",
     "label": "Take B: Neutral cadence (production standard)"},
    {"voice": DEFAULT_VOICE, "rate": "+30%", "pitch": "-10Hz",
     "label": "Take C: Deep authority (+30% speed, -10Hz pitch)"},
]


def _try_voxcpm_tts(text: str, out_path: Path, **kwargs) -> bool:
    """
    Attempt to synthesize via VoxCPM2 (https://github.com/OpenBMB/VoxCPM).
    Returns True on success, False if VoxCPM2 is unavailable.
    CPU + ~4 GB RAM: will attempt ONNX CPU inference.
    """
    try:
        import voxcpm  # type: ignore  # noqa: F401
        # VoxCPM API surface is still evolving; use subprocess call pattern
        result = subprocess.run(
            ["python", "-m", "voxcpm", "--text", text, "--output", str(out_path)],
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0 and out_path.exists() and out_path.stat().st_size > 1000
    except (ImportError, FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


async def _synthesize_edge_take(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    out_path: Path,
) -> bool:
    """Synthesize a single take using Edge-TTS."""
    try:
        import edge_tts  # type: ignore
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(str(out_path))
        return out_path.exists() and out_path.stat().st_size > 500
    except Exception as e:
        print(f"[VoiceLab] Edge-TTS take failed: {e}")
        return False


class TTSVoiceLab:
    """
    Gate 3 Voice Lab: generate 3 narrator takes for producer approval.
    Call .generate_takes() to produce the WAV files, then present them
    to the user before proceeding with the full TTS render.
    """

    def __init__(self, lab_dir: Path | None = None):
        self.lab_dir = lab_dir or Path("workspace/voice_lab")
        self.lab_dir.mkdir(parents=True, exist_ok=True)

    def generate_takes(
        self,
        hook_sentence: str,
        force: bool = False,
    ) -> List[Tuple[str, Path, str]]:
        """
        Produce 3 narrator audio takes of `hook_sentence`.

        Returns list of (label, wav_path, engine_used) tuples.
        Always returns 3 entries; entries with failed synthesis have
        wav_path pointing to an empty file and engine_used = "FAILED".
        """
        results: List[Tuple[str, Path, str]] = []
        text = hook_sentence.strip()
        if not text:
            text = "Welcome to the investigation."

        print("[VoiceLab] Generating 3 narrator takes for Gate 3 approval...")
        print(f"  Text: \"{text[:80]}{'...' if len(text) > 80 else ''}\"")

        for idx, cfg in enumerate(_TAKE_CONFIGS, start=1):
            out_path = self.lab_dir / f"take_{idx}_{cfg['voice'][:8]}.wav"
            if not force and out_path.exists() and out_path.stat().st_size > 500:
                print(f"  [Take {idx}] Cached: {out_path.name}")
                results.append((cfg["label"], out_path, "cached"))
                continue

            # 1. Try VoxCPM2
            if _try_voxcpm_tts(text, out_path):
                print(f"  [Take {idx}] VoxCPM2: {out_path.name}")
                results.append((cfg["label"], out_path, "VoxCPM2"))
                continue

            # 2. Edge-TTS fallback
            print(f"  [Take {idx}] VoxCPM2 unavailable (no GPU / not installed) — using Edge-TTS ...")
            ok = asyncio.run(
                _synthesize_edge_take(
                    text=text,
                    voice=cfg["voice"],
                    rate=cfg["rate"],
                    pitch=cfg["pitch"],
                    out_path=out_path,
                )
            )
            if ok:
                print(f"  [Take {idx}] Edge-TTS {cfg['voice']} {cfg['rate']}: {out_path.name}")
                results.append((cfg["label"], out_path, "Edge-TTS"))
            else:
                print(f"  [Take {idx}] FAILED — both VoxCPM2 and Edge-TTS failed for this take.")
                # Write empty placeholder so pipeline knows
                out_path.write_bytes(b"")
                results.append((cfg["label"], out_path, "FAILED"))

        self._print_gate3_report(results)
        return results

    def _print_gate3_report(self, results: List[Tuple[str, Path, str]]) -> None:
        print("\n" + "=" * 60)
        print("GATE 3 — VOICE LAB RESULTS")
        print("=" * 60)
        for label, path, engine in results:
            status = "READY" if path.stat().st_size > 500 else "FAILED"
            print(f"  [{status}] {label}")
            print(f"         Engine : {engine}")
            print(f"         File   : {path}")
        print("=" * 60)
        print("Listen to the takes above and choose your narrator persona.")
        print("The full render will use the same Edge-TTS voice configuration.")
        print("=" * 60 + "\n")
