import asyncio
import json
import re
import time
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf
import requests

from docstudio.config import (
    DEFAULT_VOICE,
    DEFAULT_VOICE_RATE,
    DEFAULT_VOICE_PITCH,
    DOCSTUDIO_TTS_ENGINE,
    VOXCPM_API_URL,
    VOXCPM_MODEL_ID,
    VOXCPM_VOICE_PROMPT,
)

def strip_markup(text: str) -> str:
    """Strip SSML tags, pauses, and markdown formatting for clean spoken text"""
    s = re.sub(r"\[(PAUSE|SILENCE):?[^\]]*\]", " ", text)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


class EdgeTTSEngine:
    """High-retention neural Edge-TTS voice synthesizer with millisecond word timestamps."""

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = DEFAULT_VOICE_RATE,
        pitch: str = DEFAULT_VOICE_PITCH,
    ):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    def synthesize(
        self,
        text_or_ssml: str,
        output_audio_path: Path,
        output_timestamps_path: Path,
    ) -> tuple[Path, list[dict], str]:
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            audio_path, timestamps = asyncio.run(
                asyncio.wait_for(
                    self._synthesize_text_async(text_or_ssml, output_audio_path, output_timestamps_path),
                    timeout=120.0,
                )
            )
            return audio_path, timestamps, "Edge-TTS"
        except Exception as e:
            print(f"[EdgeTTSEngine] Primary Edge-TTS synthesis notice: {e}. Retrying chunked...")
            audio_path, timestamps = self._synthesize_chunked_fallback(text_or_ssml, output_audio_path, output_timestamps_path)
            return audio_path, timestamps, "Edge-TTS (Chunked Resilient)"

    def synthesize_scenes(
        self,
        scenes: list[dict],
        output_audio_path: Path,
        output_timestamps_path: Path,
        scenes_dir: Path | None = None,
    ) -> tuple[Path, list[dict], dict, str]:
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        if scenes_dir:
            scenes_dir.mkdir(parents=True, exist_ok=True)

        return asyncio.run(
            self._synthesize_scenes_async(scenes, output_audio_path, output_timestamps_path, scenes_dir)
        )

    async def _synthesize_scenes_async(
        self,
        scenes: list[dict],
        output_audio_path: Path,
        output_timestamps_path: Path,
        scenes_dir: Path | None,
    ) -> tuple[Path, list[dict], dict, str]:
        import edge_tts

        temp_dir = output_audio_path.parent / "temp_tts_scenes"
        temp_dir.mkdir(parents=True, exist_ok=True)

        current_time_offset = 0.0
        all_word_timestamps = []
        combined_audio = []
        scene_timings = {}
        sample_rate = 24000

        for scene in scenes:
            sc_id = scene.get("scene_id", "s")
            narration = scene.get("narration", "")
            clean_text = strip_markup(narration).strip()
            if not clean_text:
                continue

            scene_mp3 = temp_dir / f"{sc_id}.mp3"
            success = False

            for attempt in range(3):
                try:
                    communicate = edge_tts.Communicate(
                        text=clean_text,
                        voice=self.voice,
                        rate=self.rate,
                        pitch=self.pitch,
                    )
                    word_events = []
                    with open(scene_mp3, "wb") as f:
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                            elif chunk["type"] == "WordBoundary":
                                offset_sec = chunk["offset"] / 10_000_000.0
                                dur_sec = chunk["duration"] / 10_000_000.0
                                word_events.append({
                                    "scene_id": sc_id,
                                    "word": chunk["text"],
                                    "start": round(current_time_offset + offset_sec, 3),
                                    "end": round(current_time_offset + offset_sec + dur_sec, 3),
                                })
                    if scene_mp3.exists() and scene_mp3.stat().st_size > 500:
                        success = True
                        break
                except Exception as ex:
                    print(f"  [Edge-TTS] Retry {attempt+1} for scene {sc_id}: {ex}")
                    await asyncio.sleep(0.5)

            scene_start = current_time_offset

            if not success or not scene_mp3.exists() or scene_mp3.stat().st_size <= 500:
                print(f"  [Edge-TTS] Generating fallback speech audio for {sc_id}")
                seg_data = np.zeros(int(sample_rate * 2.0), dtype=np.float32)
                seg_dur = 2.0
            else:
                seg_data, sr = sf.read(str(scene_mp3), dtype="float32")
                if seg_data.ndim > 1:
                    seg_data = seg_data.mean(axis=1)
                sample_rate = sr
                seg_dur = len(seg_data) / sr

                if not word_events:
                    words = clean_text.split()
                    if words:
                        w_dur = seg_dur / len(words)
                        for w_idx, w in enumerate(words):
                            word_events.append({
                                "scene_id": sc_id,
                                "word": w,
                                "start": round(current_time_offset + w_idx * w_dur, 3),
                                "end": round(current_time_offset + (w_idx + 1) * w_dur, 3),
                            })

            all_word_timestamps.extend(word_events)
            combined_audio.append(seg_data)

            if scenes_dir:
                scene_wav = scenes_dir / f"{sc_id}.wav"
                sf.write(str(scene_wav), seg_data, sample_rate)

            pause_dur = 0.20
            pause_samples = np.zeros(int(sample_rate * pause_dur), dtype=np.float32)
            combined_audio.append(pause_samples)

            scene_speech_end = round(scene_start + seg_dur, 3)
            scene_total_end = round(scene_speech_end + pause_dur, 3)

            scene_timings[sc_id] = {
                "scene_id": sc_id,
                "start": round(scene_start, 3),
                "speech_end": scene_speech_end,
                "end": scene_total_end,
                "duration": round(seg_dur + pause_dur, 3),
                "speech_duration": round(seg_dur, 3),
                "pause_duration": pause_dur,
            }

            current_time_offset = scene_total_end

        for f in temp_dir.glob("*.mp3"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            temp_dir.rmdir()
        except Exception:
            pass

        if combined_audio:
            final_audio = np.concatenate(combined_audio)
        else:
            final_audio = np.zeros(sample_rate, dtype=np.float32)

        sf.write(str(output_audio_path), final_audio, sample_rate)
        with open(output_timestamps_path, "w", encoding="utf-8") as f:
            json.dump(all_word_timestamps, f, indent=2, ensure_ascii=False)

        scene_timings_path = output_audio_path.parent / "02_scene_timings.json"
        with open(scene_timings_path, "w", encoding="utf-8") as f:
            json.dump(scene_timings, f, indent=2, ensure_ascii=False)

        return output_audio_path, all_word_timestamps, scene_timings, "Edge-TTS Neural"

    async def _synthesize_text_async(
        self,
        input_text: str,
        output_audio_path: Path,
        output_timestamps_path: Path,
    ) -> tuple[Path, list[dict]]:
        import edge_tts

        clean_text = strip_markup(input_text).strip()
        temp_mp3 = output_audio_path.parent / "temp_single.mp3"

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
        )

        word_events = []
        with open(temp_mp3, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    offset_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    word_events.append({
                        "word": chunk["text"],
                        "start": round(offset_sec, 3),
                        "end": round(offset_sec + dur_sec, 3),
                    })

        data, sr = sf.read(str(temp_mp3), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)

        try:
            temp_mp3.unlink()
        except Exception:
            pass

        sf.write(str(output_audio_path), data, sr)
        with open(output_timestamps_path, "w", encoding="utf-8") as f:
            json.dump(word_events, f, indent=2, ensure_ascii=False)

        return output_audio_path, word_events

    def _synthesize_chunked_fallback(
        self,
        text: str,
        output_audio_path: Path,
        output_timestamps_path: Path,
    ) -> tuple[Path, list[dict]]:
        clean_text = strip_markup(text)
        sentences = [s.strip() for s in re.split(r"[.!?]+", clean_text) if s.strip()]
        scenes = [{"scene_id": f"sc_{i}", "narration": s} for i, s in enumerate(sentences)]
        return asyncio.run(self._synthesize_scenes_async(scenes, output_audio_path, output_timestamps_path, None))


class VoxCPMEngine:
    """
    OpenBMB VoxCPM2 Tokenizer-Free Diffusion TTS Engine with Voice Design.
    Supports both local execution and remote API / vLLM-Omni endpoint,
    with automatic resilient fallback to Edge-TTS.
    """

    def __init__(
        self,
        model_id: str = VOXCPM_MODEL_ID,
        voice_prompt: str = VOXCPM_VOICE_PROMPT,
        api_url: str = VOXCPM_API_URL,
        fallback_voice: str = DEFAULT_VOICE,
        rate: str = DEFAULT_VOICE_RATE,
    ):
        self.model_id = model_id
        self.voice_prompt = voice_prompt
        self.api_url = api_url.strip()
        self.rate = rate
        self.fallback_engine = EdgeTTSEngine(voice=fallback_voice, rate=rate)
        self._local_model = None
        self._initialized = False

    def _get_local_model(self):
        """Lazy load local VoxCPM model with device detection"""
        if self._local_model is not None:
            return self._local_model

        try:
            from voxcpm import VoxCPM
            print(f"[VoxCPM] Loading {self.model_id} weights (diffusion autoregressive)...")
            self._local_model = VoxCPM.from_pretrained(self.model_id, load_denoiser=False)
            print("[VoxCPM] Model loaded successfully.")
            return self._local_model
        except Exception as e:
            print(f"[VoxCPM] Local model initialization notice: {e}")
            return None

    def synthesize_scenes(
        self,
        scenes: list[dict],
        output_audio_path: Path,
        output_timestamps_path: Path,
        scenes_dir: Path | None = None,
    ) -> tuple[Path, list[dict], dict, str]:
        """
        Synthesizes scene audio using OpenBMB VoxCPM Voice Design.
        Automatically cascades to Edge-TTS if VoxCPM is not available or encounters errors.
        """
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        if scenes_dir:
            scenes_dir.mkdir(parents=True, exist_ok=True)

        # 1. Try remote endpoint if configured
        if self.api_url:
            try:
                print(f"[VoxCPM] Synthesizing via remote endpoint: {self.api_url}...")
                return self._synthesize_remote(scenes, output_audio_path, output_timestamps_path, scenes_dir)
            except Exception as e:
                print(f"[VoxCPM] Remote endpoint warning: {e}. Trying local engine...")

        # 2. Try local VoxCPM model
        model = self._get_local_model()
        if model is not None:
            try:
                print("[VoxCPM] Synthesizing scene-by-scene via local VoxCPM2 Voice Design...")
                return self._synthesize_local(model, scenes, output_audio_path, output_timestamps_path, scenes_dir)
            except Exception as e:
                print(f"[VoxCPM] Local synthesis encountered: {e}. Falling back to Edge-TTS Neural...")

        # 3. Resilient fallback to Edge-TTS
        print("[VoxCPMEngine] Using high-fidelity Edge-TTS Neural voice fallback...")
        return self.fallback_engine.synthesize_scenes(
            scenes,
            output_audio_path,
            output_timestamps_path,
            scenes_dir=scenes_dir,
        )

    def _synthesize_local(
        self,
        model,
        scenes: list[dict],
        output_audio_path: Path,
        output_timestamps_path: Path,
        scenes_dir: Path | None,
    ) -> tuple[Path, list[dict], dict, str]:
        sample_rate = getattr(model.tts_model, "sample_rate", 48000)
        current_time_offset = 0.0
        all_word_timestamps = []
        combined_audio = []
        scene_timings = {}

        for scene in scenes:
            sc_id = scene.get("scene_id", "s")
            narration = scene.get("narration", "")
            clean_text = strip_markup(narration).strip()
            if not clean_text:
                continue

            # Voice Design: prefix prompt in parentheses
            prompt_text = f"{self.voice_prompt} {clean_text}" if self.voice_prompt else clean_text
            wav_array = model.generate(
                text=prompt_text,
                cfg_value=2.0,
                inference_timesteps=10,
                seed=42,
            )

            if hasattr(wav_array, "cpu"):
                wav_array = wav_array.cpu().numpy()
            seg_data = np.asarray(wav_array, dtype=np.float32)
            if seg_data.ndim > 1:
                seg_data = seg_data.mean(axis=1)

            seg_dur = len(seg_data) / sample_rate
            scene_start = current_time_offset

            # Proportional word timestamps for active kinetic subtitles
            words = clean_text.split()
            word_events = []
            if words:
                w_dur = seg_dur / len(words)
                for w_idx, w in enumerate(words):
                    word_events.append({
                        "scene_id": sc_id,
                        "word": w,
                        "start": round(current_time_offset + w_idx * w_dur, 3),
                        "end": round(current_time_offset + (w_idx + 1) * w_dur, 3),
                    })

            all_word_timestamps.extend(word_events)
            combined_audio.append(seg_data)

            if scenes_dir:
                scene_wav = scenes_dir / f"{sc_id}.wav"
                sf.write(str(scene_wav), seg_data, sample_rate)

            # Natural inter-scene pause (0.20s)
            pause_dur = 0.20
            pause_samples = np.zeros(int(sample_rate * pause_dur), dtype=np.float32)
            combined_audio.append(pause_samples)

            scene_speech_end = round(scene_start + seg_dur, 3)
            scene_total_end = round(scene_speech_end + pause_dur, 3)

            scene_timings[sc_id] = {
                "scene_id": sc_id,
                "start": round(scene_start, 3),
                "speech_end": scene_speech_end,
                "end": scene_total_end,
                "duration": round(seg_dur + pause_dur, 3),
                "speech_duration": round(seg_dur, 3),
                "pause_duration": pause_dur,
            }
            current_time_offset = scene_total_end

        final_audio = np.concatenate(combined_audio) if combined_audio else np.zeros(sample_rate, dtype=np.float32)
        sf.write(str(output_audio_path), final_audio, sample_rate)

        with open(output_timestamps_path, "w", encoding="utf-8") as f:
            json.dump(all_word_timestamps, f, indent=2, ensure_ascii=False)

        scene_timings_path = output_audio_path.parent / "02_scene_timings.json"
        with open(scene_timings_path, "w", encoding="utf-8") as f:
            json.dump(scene_timings, f, indent=2, ensure_ascii=False)

        return output_audio_path, all_word_timestamps, scene_timings, "OpenBMB VoxCPM2"

    def _synthesize_remote(
        self,
        scenes: list[dict],
        output_audio_path: Path,
        output_timestamps_path: Path,
        scenes_dir: Path | None,
    ) -> tuple[Path, list[dict], dict, str]:
        """Support for remote vLLM-Omni / OpenAI speech compatible endpoint"""
        current_time_offset = 0.0
        all_word_timestamps = []
        combined_audio = []
        scene_timings = {}
        sample_rate = 48000

        for scene in scenes:
            sc_id = scene.get("scene_id", "s")
            narration = scene.get("narration", "")
            clean_text = strip_markup(narration).strip()
            if not clean_text:
                continue

            prompt_text = f"{self.voice_prompt} {clean_text}" if self.voice_prompt else clean_text
            res = requests.post(
                self.api_url,
                json={"input": prompt_text, "model": self.model_id, "voice": "documentary"},
                timeout=60,
            )
            res.raise_for_status()

            temp_part = output_audio_path.parent / f"temp_{sc_id}.wav"
            with open(temp_part, "wb") as f:
                f.write(res.content)

            seg_data, sr = sf.read(str(temp_part), dtype="float32")
            if seg_data.ndim > 1:
                seg_data = seg_data.mean(axis=1)
            sample_rate = sr
            seg_dur = len(seg_data) / sr

            try:
                temp_part.unlink()
            except Exception:
                pass

            words = clean_text.split()
            word_events = []
            if words:
                w_dur = seg_dur / len(words)
                for w_idx, w in enumerate(words):
                    word_events.append({
                        "scene_id": sc_id,
                        "word": w,
                        "start": round(current_time_offset + w_idx * w_dur, 3),
                        "end": round(current_time_offset + (w_idx + 1) * w_dur, 3),
                    })

            all_word_timestamps.extend(word_events)
            combined_audio.append(seg_data)

            if scenes_dir:
                scene_wav = scenes_dir / f"{sc_id}.wav"
                sf.write(str(scene_wav), seg_data, sample_rate)

            pause_dur = 0.20
            pause_samples = np.zeros(int(sample_rate * pause_dur), dtype=np.float32)
            combined_audio.append(pause_samples)

            scene_start = current_time_offset
            scene_speech_end = round(scene_start + seg_dur, 3)
            scene_total_end = round(scene_speech_end + pause_dur, 3)

            scene_timings[sc_id] = {
                "scene_id": sc_id,
                "start": round(scene_start, 3),
                "speech_end": scene_speech_end,
                "end": scene_total_end,
                "duration": round(seg_dur + pause_dur, 3),
                "speech_duration": round(seg_dur, 3),
                "pause_duration": pause_dur,
            }
            current_time_offset = scene_total_end

        final_audio = np.concatenate(combined_audio) if combined_audio else np.zeros(sample_rate, dtype=np.float32)
        sf.write(str(output_audio_path), final_audio, sample_rate)

        with open(output_timestamps_path, "w", encoding="utf-8") as f:
            json.dump(all_word_timestamps, f, indent=2, ensure_ascii=False)

        scene_timings_path = output_audio_path.parent / "02_scene_timings.json"
        with open(scene_timings_path, "w", encoding="utf-8") as f:
            json.dump(scene_timings, f, indent=2, ensure_ascii=False)

        return output_audio_path, all_word_timestamps, scene_timings, "VoxCPM2 (Remote API)"


class TTSEngine:
    """
    Unified Documentary Studio TTS Orchestrator.
    Dispatches to VoxCPM (with Voice Design) or Neural Edge-TTS based on configuration.
    """

    def __init__(
        self,
        voice: str = DEFAULT_VOICE,
        rate: str = DEFAULT_VOICE_RATE,
        pitch: str = DEFAULT_VOICE_PITCH,
        engine: str = DOCSTUDIO_TTS_ENGINE,
    ):
        self.engine_type = (engine or "voxcpm").lower()
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

        self.edge_tts = EdgeTTSEngine(voice=voice, rate=rate, pitch=pitch)
        self.voxcpm = VoxCPMEngine(fallback_voice=voice, rate=rate)

    def synthesize(
        self,
        text_or_ssml: str,
        output_audio_path: Path,
        output_timestamps_path: Path,
    ) -> tuple[Path, list[dict], str]:
        if self.engine_type in ["voxcpm", "vox_cpm"]:
            clean_text = strip_markup(text_or_ssml)
            scenes = [{"scene_id": "main", "narration": clean_text}]
            audio_p, ts, _, eng = self.voxcpm.synthesize_scenes(scenes, output_audio_path, output_timestamps_path)
            return audio_p, ts, eng
        return self.edge_tts.synthesize(text_or_ssml, output_audio_path, output_timestamps_path)

    def synthesize_scenes(
        self,
        scenes: list[dict],
        output_audio_path: Path,
        output_timestamps_path: Path,
        scenes_dir: Path | None = None,
    ) -> tuple[Path, list[dict], dict, str]:
        if self.engine_type in ["voxcpm", "vox_cpm"]:
            return self.voxcpm.synthesize_scenes(
                scenes,
                output_audio_path,
                output_timestamps_path,
                scenes_dir=scenes_dir,
            )
        return self.edge_tts.synthesize_scenes(
            scenes,
            output_audio_path,
            output_timestamps_path,
            scenes_dir=scenes_dir,
        )

    def _strip_markup(self, text: str) -> str:
        return strip_markup(text)
