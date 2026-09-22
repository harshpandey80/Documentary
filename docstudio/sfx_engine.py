import math
import numpy as np
import soundfile as sf
from pathlib import Path
from docstudio.config import SFX_DIR

def generate_default_sfx_library(output_dir: Path = SFX_DIR) -> dict[str, Path]:
    """
    Synthesize high-quality, royalty-free cinematic documentary sound effects 
    (Whoosh, Deep Braam, Riser, Ambient Tension Drone, Impact Hit) using procedural audio.
    Guarantees 100% copyright-safe, self-hosted audio beds out of the box.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    generated_files = {}

    # 1. Whoosh Transition (0.8 seconds)
    whoosh_path = output_dir / "whoosh.wav"
    if not whoosh_path.exists():
        duration = 0.8
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Filtered noise sweep
        noise = np.random.uniform(-1, 1, len(t))
        # Envelope: rise and fall
        env = np.sin(np.pi * (t / duration)) ** 2
        # Modulating frequency
        carrier = np.sin(2 * np.pi * (200 + 400 * np.sin(np.pi * t / duration)) * t)
        whoosh = (noise * 0.7 + carrier * 0.3) * env
        whoosh = whoosh / np.max(np.abs(whoosh) + 1e-6) * 0.7
        sf.write(str(whoosh_path), whoosh.astype(np.float32), sample_rate)
    generated_files["whoosh"] = whoosh_path

    # 2. Deep Cinematic Braam / Sub Impact (2.5 seconds)
    braam_path = output_dir / "deep_braam.wav"
    if not braam_path.exists():
        duration = 2.5
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Deep low sub frequencies (55Hz A1, 110Hz A2) + slight distortion
        f1, f2, f3 = 55.0, 110.0, 165.0
        pitch_drop = np.exp(-1.5 * t)
        sound = (
            0.6 * np.sin(2 * np.pi * (f1 * (1 + 0.3 * pitch_drop)) * t) +
            0.3 * np.sin(2 * np.pi * (f2 * (1 + 0.2 * pitch_drop)) * t) +
            0.2 * np.sin(2 * np.pi * (f3 * (1 + 0.1 * pitch_drop)) * t)
        )
        # Soft saturation distortion for brassy punch
        sound = np.tanh(sound * 2.5)
        # Exponential decay envelope
        decay = np.exp(-1.2 * t)
        # Quick attack
        attack = np.minimum(t / 0.05, 1.0)
        braam = sound * decay * attack
        braam = braam / np.max(np.abs(braam) + 1e-6) * 0.8
        sf.write(str(braam_path), braam.astype(np.float32), sample_rate)
    generated_files["deep_braam"] = braam_path

    # 3. Tension Riser (2.0 seconds)
    riser_path = output_dir / "riser.wav"
    if not riser_path.exists():
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        # Frequency rising from 100Hz to 900Hz
        freq = 100.0 + 800.0 * (t / duration) ** 2
        phase = 2 * np.pi * np.cumsum(freq) / sample_rate
        noise = np.random.uniform(-0.3, 0.3, len(t))
        tone = np.sin(phase) + noise * (t / duration)
        # Linear crescendo
        env = (t / duration) ** 1.5
        riser = tone * env
        riser = riser / np.max(np.abs(riser) + 1e-6) * 0.7
        sf.write(str(riser_path), riser.astype(np.float32), sample_rate)
    generated_files["riser"] = riser_path

    # 4. Impact Hit (1.2 seconds)
    hit_path = output_dir / "impact_hit.wav"
    if not hit_path.exists():
        duration = 1.2
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        sub = np.sin(2 * np.pi * 70 * np.exp(-6 * t) * t) * np.exp(-4 * t)
        noise_burst = np.random.uniform(-1, 1, len(t)) * np.exp(-15 * t)
        hit = (sub * 0.7 + noise_burst * 0.5)
        hit = hit / np.max(np.abs(hit) + 1e-6) * 0.8
        sf.write(str(hit_path), hit.astype(np.float32), sample_rate)
    generated_files["impact_hit"] = hit_path

    # 5. Ambient Tension Bed (Loopable 15 seconds)
    ambient_tension_path = output_dir / "ambient_tension.wav"
    if not ambient_tension_path.exists():
        duration = 15.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        chord = (
            0.4 * np.sin(2 * np.pi * 65.4 * t) +
            0.3 * np.sin(2 * np.pi * 77.8 * t) +
            0.35 * np.sin(2 * np.pi * 98.0 * t) +
            0.15 * np.sin(2 * np.pi * 130.8 * t)
        )
        lfo = 0.7 + 0.3 * np.sin(2 * np.pi * 0.2 * t)
        drone = chord * lfo
        fade_len = int(sample_rate * 0.5)
        drone[:fade_len] *= np.linspace(0, 1, fade_len)
        drone[-fade_len:] *= np.linspace(1, 0, fade_len)
        drone = drone / np.max(np.abs(drone) + 1e-6) * 0.6
        sf.write(str(ambient_tension_path), drone.astype(np.float32), sample_rate)
    generated_files["ambient_tension"] = ambient_tension_path

    # 6. Ambient Reveal Bed (Loopable 15 seconds)
    ambient_reveal_path = output_dir / "ambient_reveal.wav"
    if not ambient_reveal_path.exists():
        duration = 15.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        shimmer = (
            0.35 * np.sin(2 * np.pi * 146.8 * t) +
            0.3 * np.sin(2 * np.pi * 220.0 * t) +
            0.25 * np.sin(2 * np.pi * 370.0 * t) +
            0.15 * np.sin(2 * np.pi * 440.0 * t + np.sin(2 * np.pi * 0.5 * t))
        )
        lfo = 0.8 + 0.2 * np.sin(2 * np.pi * 0.35 * t)
        drone = shimmer * lfo
        fade_len = int(sample_rate * 0.5)
        drone[:fade_len] *= np.linspace(0, 1, fade_len)
        drone[-fade_len:] *= np.linspace(1, 0, fade_len)
        drone = drone / np.max(np.abs(drone) + 1e-6) * 0.6
        sf.write(str(ambient_reveal_path), drone.astype(np.float32), sample_rate)
    generated_files["ambient_reveal"] = ambient_reveal_path

    # 7. Ambient Somber Bed (Loopable 15 seconds)
    ambient_somber_path = output_dir / "ambient_somber.wav"
    if not ambient_somber_path.exists():
        duration = 15.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        somber = (
            0.5 * np.sin(2 * np.pi * 55.0 * t) +
            0.35 * np.sin(2 * np.pi * 65.4 * t) +
            0.2 * np.sin(2 * np.pi * 82.4 * t)
        )
        lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.1 * t)
        drone = somber * lfo
        fade_len = int(sample_rate * 0.5)
        drone[:fade_len] *= np.linspace(0, 1, fade_len)
        drone[-fade_len:] *= np.linspace(1, 0, fade_len)
        drone = drone / np.max(np.abs(drone) + 1e-6) * 0.6
        sf.write(str(ambient_somber_path), drone.astype(np.float32), sample_rate)
    generated_files["ambient_somber"] = ambient_somber_path

    # 8. Ambient Triumphant Bed (Loopable 15 seconds)
    ambient_triumphant_path = output_dir / "ambient_triumphant.wav"
    if not ambient_triumphant_path.exists():
        duration = 15.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        tri = (
            0.4 * np.sin(2 * np.pi * 130.8 * t) +
            0.35 * np.sin(2 * np.pi * 196.0 * t) +
            0.3 * np.sin(2 * np.pi * 261.6 * t) +
            0.2 * np.sin(2 * np.pi * 329.6 * t)
        )
        lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t)
        drone = tri * lfo
        fade_len = int(sample_rate * 0.5)
        drone[:fade_len] *= np.linspace(0, 1, fade_len)
        drone[-fade_len:] *= np.linspace(1, 0, fade_len)
        drone = drone / np.max(np.abs(drone) + 1e-6) * 0.6
        sf.write(str(ambient_triumphant_path), drone.astype(np.float32), sample_rate)
    generated_files["ambient_triumphant"] = ambient_triumphant_path

    # 9. Ambient Drone Bed (Loopable 15 seconds)
    ambient_drone_path = output_dir / "ambient_drone.wav"
    if not ambient_drone_path.exists():
        duration = 15.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        sub = 0.6 * np.sin(2 * np.pi * 55.0 * t) + 0.25 * np.sin(2 * np.pi * 110.0 * t)
        noise = np.random.uniform(-0.02, 0.02, len(t))
        drone = (sub + noise) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.15 * t))
        fade_len = int(sample_rate * 0.5)
        drone[:fade_len] *= np.linspace(0, 1, fade_len)
        drone[-fade_len:] *= np.linspace(1, 0, fade_len)
        drone = drone / np.max(np.abs(drone) + 1e-6) * 0.6
        sf.write(str(ambient_drone_path), drone.astype(np.float32), sample_rate)
    generated_files["ambient_drone"] = ambient_drone_path

    return generated_files

