import subprocess
import numpy as np
import soundfile as sf
from pathlib import Path
from docstudio.config import SFX_DIR
from docstudio.cinematic_audio import CinematicAudioEngine

class AudioMixer:
    def __init__(self, sfx_dir: Path = SFX_DIR):
        self.sfx_dir = sfx_dir
        self.engine = CinematicAudioEngine(sample_rate=44100)

    def mix_master_audio(
        self,
        voice_audio_path: Path,
        word_timestamps: list[dict],
        scenes: list[dict],
        output_path: Path,
        music_bed_path: Path | None = None,
        scene_timings: dict | None = None,
    ) -> Path:
        """
        Produce an industry-standard broadcast documentary audio master:
        1. Layer 1: Clean voiceover narration (-11 dBFS)
        2. Layer 2: Evolving harmonic music bed with smooth sidechain ducking
        3. Layer 3: Analog room tone & tape warmth (-27 dBFS)
        4. Layer 4: Sparsely spaced SFX (locked to scene transitions & downbeats)
        5. EBU R128 loudness normalization to -14.0 LUFS (-1 dBTP)
        """
        voice_data, sample_rate = sf.read(str(voice_audio_path), dtype="float32")
        if voice_data.ndim > 1:
            voice_data = voice_data.mean(axis=1)

        # Ensure sample rate consistency
        if sample_rate != self.engine.sr:
            t_len = int(len(voice_data) * (self.engine.sr / sample_rate))
            voice_data = np.interp(np.linspace(0, len(voice_data), t_len), np.arange(len(voice_data)), voice_data)
            sample_rate = self.engine.sr

        raw_mixed_path = output_path.parent / "temp_raw_mix.wav"
        self.engine.mix_documentary_score(
            voice_data=voice_data,
            word_timestamps=word_timestamps,
            scenes=scenes,
            output_file=raw_mixed_path,
            scene_timings=scene_timings,
        )

        # Two-Pass EBU R128 Loudness Normalization to -14.0 LUFS (-1 dBTP) via FFmpeg
        # Pass 1: Cascaded 4-pole highpass 85Hz + measure loudness parameters
        output_path.parent.mkdir(parents=True, exist_ok=True)
        hp_filter = "highpass=f=85:poles=2,highpass=f=85:poles=2"
        pass1_cmd = [
            "ffmpeg", "-nostats",
            "-i", str(raw_mixed_path),
            "-af", f"{hp_filter},loudnorm=I=-14:LRA=7:tp=-1.2:print_format=json",
            "-f", "null", "-"
        ]
        p1_res = subprocess.run(pass1_cmd, capture_output=True, text=True)
        
        # Parse Pass 1 JSON parameters
        import json
        import re
        input_i, input_tp, input_lra, input_thresh, target_offset = None, None, None, None, None
        try:
            m_json = re.search(r"\{[\s\S]*\"input_i\"[\s\S]*\}", p1_res.stderr)
            if m_json:
                p1_data = json.loads(m_json.group(0))
                input_i = p1_data.get("input_i")
                input_tp = p1_data.get("input_tp")
                input_lra = p1_data.get("input_lra")
                input_thresh = p1_data.get("input_thresh")
                target_offset = p1_data.get("target_offset")
        except Exception:
            pass

        # Pass 2: Apply calibrated linear loudnorm with cascaded 85Hz highpass and true peak brickwall limiter
        if input_i and input_tp and input_lra and input_thresh and target_offset:
            ln_filter = (
                f"{hp_filter},"
                f"loudnorm=I=-14:LRA=7:tp=-1.2:"
                f"measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:"
                f"measured_thresh={input_thresh}:offset={target_offset}:linear=true,"
                f"alimiter=limit=-1.2dB:attack=5:release=50"
            )
        else:
            ln_filter = f"{hp_filter},loudnorm=I=-14:LRA=7:tp=-1.2,alimiter=limit=-1.2dB:attack=5:release=50"

        norm_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_mixed_path),
            "-af", ln_filter,
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(output_path)
        ]
        res = subprocess.run(norm_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Fallback to raw mix if FFmpeg loudnorm filter is unavailable
            raw_data, _ = sf.read(str(raw_mixed_path), dtype="float32")
            sf.write(str(output_path), raw_data.astype(np.float32), 44100)

        # Clean up temporary raw mix
        if raw_mixed_path.exists():
            try:
                raw_mixed_path.unlink()
            except Exception:
                pass

        return output_path
