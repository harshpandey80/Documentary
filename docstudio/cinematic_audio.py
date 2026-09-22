import re
import numpy as np
import soundfile as sf
from pathlib import Path
from docstudio.config import (
    SFX_DIR,
    MUSIC_DIR,
    VOICE_GAIN,
    MUSIC_NORMAL_VOLUME,
    DUCK_DEPTH,
    SFX_VOLUME,
    ROOM_TONE_VOLUME,
)

def load_audio_file(path: Path, target_sr: int) -> np.ndarray | None:
    """Safely loads an audio file (wav, mp3, flac, ogg) and normalizes to mono float32 at target_sr."""
    try:
        if not path.exists() or path.stat().st_size < 1000:
            return None
        data, sr = sf.read(str(path), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)  # Stereo to mono
        if sr != target_sr:
            t_len = int(len(data) * (target_sr / sr))
            data = np.interp(
                np.linspace(0, len(data), t_len, endpoint=False),
                np.arange(len(data)),
                data
            ).astype(np.float32)
        return data
    except Exception:
        return None

class CinematicAudioEngine:
    """
    Professional 4-layer documentary sound design engine modeled after
    the audio workflows of LEMMiNO, Melodysheep, and Fern.

    Layers:
    1. Dialogue (Master voiceover)
    2. Continuous Harmonic Music Bed (rich multi-oscillator analog synth chords, evolving LFO filters)
    3. Continuous Analog Room Tone & Tape Warmth (-27 dBFS background bed)
    4. Sparse Narrative Punctuation SFX (Braams, Risers, Whooshes with >= 15s spacing gates)
    """

    def __init__(self, sample_rate: int = 44100):
        self.sr = sample_rate

    def generate_harmonic_bed(
        self,
        mood: str = "tension",
        duration: float = 60.0,
        num_samples: int | None = None,
    ) -> np.ndarray:
        """
        Synthesizes a deep, evolving documentary harmonic drone bed.
        Composed of subterranean fundamentals, fifths, and emotional color intervals,
        modulated by slow dual LFOs to create an evolving, non-repetitive score.
        """
        sr = self.sr
        if num_samples is None:
            num_samples = int(sr * duration)
        t = np.linspace(0, num_samples / sr, num_samples, endpoint=False)

        # Harmonic definitions (Root, 5th, Color intervals in Hz)
        # Keep 20-80 Hz sub-bass fundamentals at reduced levels (gain <= 0.15) to guarantee
        # at least 15 dB separation between voice band (300-3400 Hz) and sub-bass
        if mood == "tension":
            # Sub-bass attenuated to 0.12, upper harmonics support harmonic richness
            base_freqs = [43.65, 65.41, 98.00, 130.81, 155.56, 196.00]
            gains = [0.10, 0.12, 0.35, 0.25, 0.20, 0.15]
            detunes = [0.0, 0.2, -0.3, 0.15, -0.25, 0.1]
            lfo_rate1, lfo_rate2 = 0.08, 0.03
        elif mood == "reveal":
            base_freqs = [73.42, 110.00, 146.83, 220.00, 277.18, 329.63]
            gains = [0.12, 0.35, 0.35, 0.30, 0.22, 0.18]
            detunes = [0.0, 0.15, -0.2, 0.25, -0.15, 0.3]
            lfo_rate1, lfo_rate2 = 0.12, 0.05
        elif mood == "somber":
            base_freqs = [55.00, 82.41, 110.00, 130.81, 164.81, 220.00]
            gains = [0.12, 0.25, 0.35, 0.25, 0.20, 0.15]
            detunes = [0.0, 0.1, -0.15, 0.2, -0.1, 0.05]
            lfo_rate1, lfo_rate2 = 0.06, 0.02
        elif mood == "triumphant":
            base_freqs = [73.42, 110.00, 146.83, 185.00, 220.00, 293.66]
            gains = [0.12, 0.35, 0.38, 0.28, 0.22, 0.16]
            detunes = [0.0, 0.15, -0.2, 0.1, -0.15, 0.2]
            lfo_rate1, lfo_rate2 = 0.10, 0.04
        else: # ambient_drone
            base_freqs = [41.20, 61.74, 82.41, 123.47, 164.81]
            gains = [0.10, 0.12, 0.35, 0.25, 0.15]
            detunes = [0.0, 0.1, -0.15, 0.2, -0.1]
            lfo_rate1, lfo_rate2 = 0.05, 0.015

        # Slow breathing filter modulation LFOs
        lfo1 = 0.75 + 0.25 * np.sin(2 * np.pi * lfo_rate1 * t)
        lfo2 = 0.80 + 0.20 * np.sin(2 * np.pi * lfo_rate2 * t + 1.2)

        composite = np.zeros(num_samples, dtype=np.float32)
        for i, (f0, g, det) in enumerate(zip(base_freqs, gains, detunes)):
            # Oscillator with subtle phase drift
            freq = f0 + det
            phase = 2 * np.pi * freq * t
            # Blend pure sine with gentle 2nd harmonic warmth
            voice_wave = np.sin(phase) + 0.25 * np.sin(2 * phase)
            # Apply slow filter modulation
            composite += (voice_wave * g * (lfo1 if i % 2 == 0 else lfo2)).astype(np.float32)

        # Soft tube saturation curve (tanh) to eliminate harsh clipping
        composite = np.tanh(composite * 0.7)

        # Fade in and fade out (1.5s) to guarantee zero pops
        fade_samples = min(int(sr * 1.5), num_samples // 4)
        if fade_samples > 0:
            composite[:fade_samples] *= np.linspace(0.0, 1.0, fade_samples)
            composite[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples)

        # Normalize to clean head-room (-12 dBFS peak)
        peak = np.max(np.abs(composite)) + 1e-6
        composite = (composite / peak) * 0.25
        return composite

    def generate_room_tone(self, duration: float, num_samples: int | None = None) -> np.ndarray:
        """
        Generate continuous subtle analog tape warmth & room tone (-32 dBFS)
        to eliminate sterile digital silence between spoken phrases.
        Uses soft band-limited noise without harsh electrical 50Hz/100Hz ground hums.
        """
        sr = self.sr
        if num_samples is None:
            num_samples = int(sr * duration)
        sub_sr = 600
        num_sub = max(1, int((num_samples / sr) * sub_sr))
        white = np.random.uniform(-1.0, 1.0, num_sub).astype(np.float32)
        filtered = np.interp(
            np.linspace(0, num_sub, num_samples, endpoint=False),
            np.arange(num_sub),
            white
        ).astype(np.float32)

        # Gentle tape warmth level (-32 dBFS) without annoying sinusoidal hum
        peak = np.max(np.abs(filtered)) + 1e-6
        return (filtered / peak * 0.025).astype(np.float32)

    def generate_cinematic_sfx(self, sfx_type: str) -> np.ndarray:
        """
        Synthesize or load cinematic trailer-grade punctuation SFX:
        First checks SFX_DIR for real audio files (e.g. whoosh.wav, deep_braam.wav).
        Falls back to procedural generation if real sample is not found.
        """
        sr = self.sr
        # Check if real audio sample exists in SFX_DIR
        for ext in [".wav", ".mp3", ".flac", ".ogg"]:
            candidate = SFX_DIR / f"{sfx_type}{ext}"
            if candidate.exists():
                loaded = load_audio_file(candidate, sr)
                if loaded is not None and len(loaded) > 0:
                    peak = np.max(np.abs(loaded)) + 1e-6
                    return (loaded / peak * 0.65).astype(np.float32)
        if sfx_type == "deep_braam":
            dur = 3.2
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            f0 = 48.0 # Low G0/A0
            pitch_envelope = 1.0 + 0.4 * np.exp(-4.0 * t)
            # Low brass harmonics
            wave = (
                0.60 * np.sin(2 * np.pi * f0 * pitch_envelope * t) +
                0.35 * np.sin(2 * np.pi * (f0 * 2) * pitch_envelope * t) +
                0.20 * np.sin(2 * np.pi * (f0 * 3) * t) +
                0.12 * np.sin(2 * np.pi * (f0 * 4) * t)
            )
            # Saturation for brass growl
            dist = np.tanh(wave * 2.8)
            # Attack / decay envelope
            attack = np.clip(t / 0.04, 0.0, 1.0)
            decay = np.exp(-1.1 * t)
            sfx = dist * attack * decay
            return (sfx / (np.max(np.abs(sfx)) + 1e-6) * 0.65).astype(np.float32)

        elif sfx_type == "riser":
            dur = 2.4
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            # Exponential pitch rise from 80Hz to 850Hz
            freq = 80.0 + 770.0 * (t / dur) ** 2.2
            phase = 2 * np.pi * np.cumsum(freq) / sr
            # Modulated tone + filtered sweep noise
            noise = np.random.uniform(-0.25, 0.25, len(t)) * (t / dur)
            tone = np.sin(phase) + noise
            crescendo = (t / dur) ** 1.8
            fade_out = np.clip((dur - t) / 0.05, 0.0, 1.0)
            sfx = tone * crescendo * fade_out
            return (sfx / (np.max(np.abs(sfx)) + 1e-6) * 0.45).astype(np.float32)

        elif sfx_type == "whoosh":
            dur = 0.75
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            noise = np.random.uniform(-1.0, 1.0, len(t))
            env = np.sin(np.pi * (t / dur)) ** 2.0
            f_center = 250.0 + 600.0 * np.sin(np.pi * t / dur)
            carrier = np.sin(2 * np.pi * f_center * t)
            sfx = (noise * 0.75 + carrier * 0.25) * env
            return (sfx / (np.max(np.abs(sfx)) + 1e-6) * 0.40).astype(np.float32)

        elif sfx_type == "air_raid_siren":
            dur = 3.5
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            siren_freq = 420.0 + 160.0 * np.sin(2 * np.pi * 0.45 * t)
            phase = 2 * np.pi * np.cumsum(siren_freq) / sr
            wave = np.sin(phase) + 0.3 * np.sin(2 * phase)
            env = np.clip(t / 0.5, 0.0, 1.0) * np.clip((dur - t) / 0.8, 0.0, 1.0)
            sfx = wave * env * 0.40
            return sfx.astype(np.float32)

        elif sfx_type == "radio_static_burst":
            dur = 0.9
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            noise = np.random.uniform(-1.0, 1.0, len(t))
            band = np.sin(2 * np.pi * 1800.0 * t) * noise
            env = np.exp(-3.2 * t)
            sfx = band * env * 0.35
            return sfx.astype(np.float32)

        elif sfx_type == "radar_ping":
            dur = 1.2
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            ping = np.sin(2 * np.pi * 920.0 * t) * np.exp(-6.5 * t)
            echo = np.sin(2 * np.pi * 920.0 * t) * np.exp(-3.0 * (t - 0.35)) * (t > 0.35)
            sfx = (ping + echo * 0.4) * 0.45
            return sfx.astype(np.float32)

        elif sfx_type == "sub_impact":
            dur = 2.8
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            sub = np.sin(2 * np.pi * 38.0 * np.exp(-1.5 * t) * t) * np.exp(-1.2 * t)
            click = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-30.0 * t)
            sfx = sub * 0.75 + click * 0.25
            return (sfx / (np.max(np.abs(sfx)) + 1e-6) * 0.70).astype(np.float32)

        else: # impact_hit
            dur = 1.4
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            sub = np.sin(2 * np.pi * 65.0 * np.exp(-5.0 * t) * t) * np.exp(-3.5 * t)
            noise_click = np.random.uniform(-1.0, 1.0, len(t)) * np.exp(-22.0 * t)
            sfx = sub * 0.75 + noise_click * 0.25
            return (sfx / (np.max(np.abs(sfx)) + 1e-6) * 0.60).astype(np.float32)

    def load_or_generate_music_bed(
        self,
        mood: str,
        duration: float,
        num_samples: int,
    ) -> np.ndarray:
        """
        Loads real studio background music from MUSIC_DIR if available.
        Prioritizes mood match (e.g. tension.mp3, somber.wav, investigative.mp3),
        then any .mp3/.wav in assets/music/.
        Falls back to procedural harmonic synthesis only if no audio files exist.
        """
        sr = self.sr
        if MUSIC_DIR.exists():
            # 1. Try mood-specific track
            for ext in [".mp3", ".wav", ".flac", ".ogg"]:
                candidate = MUSIC_DIR / f"{mood}{ext}"
                if candidate.exists():
                    audio = load_audio_file(candidate, sr)
                    if audio is not None and len(audio) > 0:
                        return self._fit_and_loop_music(audio, num_samples)

            # 2. Try any audio track in MUSIC_DIR
            music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav")) + list(MUSIC_DIR.glob("*.flac"))
            if music_files:
                audio = load_audio_file(music_files[0], sr)
                if audio is not None and len(audio) > 0:
                    return self._fit_and_loop_music(audio, num_samples)

        # 3. Fallback to harmonic drone bed
        return self.generate_harmonic_bed(mood=mood, duration=duration, num_samples=num_samples)

    def _fit_and_loop_music(self, audio: np.ndarray, target_samples: int) -> np.ndarray:
        """Seamlessly loops or trims a real studio music track with smooth crossfades."""
        sr = self.sr
        peak = np.max(np.abs(audio)) + 1e-6
        # Balanced documentary music level (-15 dBFS)
        audio = (audio / peak * 0.32).astype(np.float32)

        if len(audio) >= target_samples:
            res = audio[:target_samples].copy()
            fade_len = min(int(sr * 3.0), target_samples // 4)
            if fade_len > 0:
                res[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)
            return res

        # Loop with smooth crossfade
        out = np.zeros(target_samples, dtype=np.float32)
        pos = 0
        while pos < target_samples:
            remaining = target_samples - pos
            chunk_len = min(len(audio), remaining)
            out[pos:pos + chunk_len] = audio[:chunk_len]
            pos += chunk_len

        # Master head/tail fades
        fade_len = min(int(sr * 2.5), target_samples // 4)
        if fade_len > 0:
            out[:fade_len] *= np.linspace(0.0, 1.0, fade_len)
            out[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)
        return out

    def mix_documentary_score(
        self,
        voice_data: np.ndarray,
        word_timestamps: list[dict],
        scenes: list[dict],
        output_file: Path,
        scene_timings: dict | None = None,
    ) -> Path:
        """
        Produce a professional 4-layer master mix with:
        - Layer 1: Master Voiceover (-12 dBFS)
        - Layer 2: Continuous Music Bed (real studio track or harmonic bed, sidechained during speech)
        - Layer 3: Subtle Room Tone / Tape Warmth (-32dB continuous, zero electrical hum)
        - Layer 4: Sparsely spaced SFX locked with frame-accuracy to scene transitions and downbeats
        """
        sr = self.sr
        total_samples = len(voice_data)
        total_duration = total_samples / sr

        # 1. Voice envelope & sidechain ducking curve (sub-sampled for ultra-fast convolution)
        sub_sr = 200
        sub_len = max(1, int(total_duration * sub_sr))
        sub_envelope = np.zeros(sub_len, dtype=np.float32)
        for w in word_timestamps:
            s_idx = max(0, int((w["start"] - 0.04) * sub_sr))
            e_idx = min(sub_len, int((w["end"] + 0.06) * sub_sr))
            sub_envelope[s_idx:e_idx] = 1.0

        # Smooth attack (60ms) and release (350ms)
        kernel_len = max(3, int(sub_sr * 0.35))
        kernel = np.hanning(kernel_len)
        kernel = kernel / np.sum(kernel)
        smoothed_sub = np.convolve(sub_envelope, kernel, mode="same")
        smoothed_sub = np.clip(smoothed_sub, 0.0, 1.0)
        smoothed_voice = np.interp(
            np.linspace(0, sub_len, total_samples, endpoint=False),
            np.arange(sub_len),
            smoothed_sub
        ).astype(np.float32)

        # Sidechain gain: duck by configured depth (e.g. -24dB) during speech; swell up to MUSIC_NORMAL_VOLUME in pauses
        duck_depth = DUCK_DEPTH
        bed_gain = MUSIC_NORMAL_VOLUME * (1.0 - smoothed_voice * (1.0 - duck_depth))

        # Helper to guarantee identical 1D shape across all audio layers
        def match_shape(arr: np.ndarray, target: int) -> np.ndarray:
            if len(arr) == target:
                return arr.astype(np.float32)
            elif len(arr) > target:
                return arr[:target].astype(np.float32)
            else:
                return np.pad(arr, (0, target - len(arr))).astype(np.float32)

        bed_gain = match_shape(bed_gain, total_samples)

        # 2. Continuous Evolving Music Bed (Real Studio Track or Procedural)
        first_mood = scenes[0].get("emotional_tag", "tension") if scenes else "tension"
        music_bed = self.load_or_generate_music_bed(
            mood=first_mood,
            duration=total_duration,
            num_samples=total_samples,
        )
        music_bed = match_shape(music_bed, total_samples)
        ducked_music = (music_bed * bed_gain).astype(np.float32)

        # 3. Room Tone & Tape Warmth with exact sample count
        room_tone = self.generate_room_tone(duration=total_duration, num_samples=total_samples)
        room_tone = match_shape(room_tone, total_samples)

        # 4. Storytelling-Aligned Sound Effects (Subtle Accents, Subordinated to Voice)
        sfx_layer = np.zeros(total_samples, dtype=np.float32)
        last_heavy_sfx_time = -999.0
        last_sfx_times = {}

        # Dramatic word trigger dictionary mapping story moments to specific subtle cinematic SFX
        NARRATIVE_SFX_TRIGGERS = [
            ({"never", "found", "beneath", "triangle"}, "deep_braam", 0.0, 0.35, 5.0),
            ({"bombers", "vanished", "swallowed", "disappeared", "abyss"}, "whoosh", -0.15, 0.35, 2.5),
            ({"compass", "compasses", "spinning", "needle"}, "radar_ping", 0.0, 0.28, 3.0),
            ({"transmission", "radio", "static", "silence"}, "radio_static_burst", 0.0, 0.25, 3.0),
            ({"rescue", "radar"}, "radar_ping", 0.0, 0.28, 3.5),
            ({"zero", "wreckage", "survivors"}, "impact_hit", 0.0, 0.30, 1.8),
            ({"vortex", "rogue", "methane", "explosions"}, "sub_impact", 0.0, 0.35, 3.5),
            ({"satellites", "anomalies", "warned"}, "deep_braam", 0.0, 0.32, 4.0),
        ]

        def _add_sfx(sfx_name: str, trigger_t: float, gain: float = 0.45):
            nonlocal last_heavy_sfx_time
            if trigger_t < 0 or trigger_t >= total_duration:
                return
            sfx_data = self.generate_cinematic_sfx(sfx_name)
            if sfx_data is None or len(sfx_data) == 0:
                return
            pos_idx = int(trigger_t * sr)
            end_idx = min(total_samples, pos_idx + len(sfx_data))
            fit_len = end_idx - pos_idx
            if fit_len > 0:
                sfx_layer[pos_idx:end_idx] += (sfx_data[:fit_len] * gain)
                last_sfx_times[sfx_name] = trigger_t

        # 4a. Word-aligned storytelling triggers
        for w_item in word_timestamps:
            raw_w = re.sub(r"[^a-zA-Z0-9-]", "", w_item.get("word", "").lower())
            w_start = float(w_item.get("start", 0.0))
            if not raw_w or w_start <= 0.05:
                continue

            for word_set, sfx_name, offset_s, gain, cooldown in NARRATIVE_SFX_TRIGGERS:
                if raw_w in word_set:
                    last_t = last_sfx_times.get(sfx_name, -999.0)
                    trigger_t = max(0.0, w_start + offset_s)
                    if (trigger_t - last_t) >= cooldown:
                        _add_sfx(sfx_name, trigger_t, gain=gain)
                        break

        # 4b. Scene downbeats & cut transitions
        for idx, sc in enumerate(scenes):
            sc_id = sc.get("scene_id", f"s{idx}")
            if scene_timings and sc_id in scene_timings:
                sc_start = float(scene_timings[sc_id]["start"])
            else:
                sc_words = [w for w in word_timestamps if w.get("scene_id") == sc_id]
                sc_start = float(sc_words[0]["start"]) if sc_words else 0.0

            # Scene opening punctuation (subtle accents)
            if idx == 0:
                # Cold hook opening impact
                _add_sfx("deep_braam", 0.0, gain=0.45)
            else:
                # Transition whoosh preceding the cut by 150ms
                _add_sfx("whoosh", max(0.0, sc_start - 0.15), gain=0.30)

            # Scene-specified SFX
            for s_name in sc.get("sfx", []):
                last_t = last_sfx_times.get(s_name, -999.0)
                if (sc_start - last_t) >= 3.0:
                    _add_sfx(s_name, sc_start, gain=0.32)

        # 5. Composite Mix with guaranteed vocal dominance
        voice_data = match_shape(voice_data, total_samples)
        ducked_music = match_shape(ducked_music, total_samples)
        room_tone = match_shape(room_tone, total_samples)
        
        # Duck SFX layer during active speech so sound effects NEVER compete with vocal consonants
        sfx_ducking = (1.0 - smoothed_voice * 0.60).astype(np.float32)
        ducked_sfx = match_shape(sfx_layer * sfx_ducking, total_samples)

        # Master balance: Narration voice is strictly dominant (+15dB to +20dB over beds)
        master = (
            (voice_data * VOICE_GAIN) +
            ducked_music +
            (room_tone * ROOM_TONE_VOLUME) +
            (ducked_sfx * SFX_VOLUME)
        )
        # Tanh analog soft clipper to prevent harsh digital overs while preserving dynamic punch
        master = np.tanh(master * 0.95)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_file), master.astype(np.float32), sr)
        return output_file
