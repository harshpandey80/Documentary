# InVideo AI Documentary Studio: Autonomous Video Production Platform

InVideo AI Documentary Studio is a full-stack, automated video production studio that turns a prompt, topic, or investigative headline into a high-retention, broadcast-ready 1080p MP4 video with real moving stock B-roll video footage, studio neural voiceover, animated karaoke subtitles, dynamic music ducking, and distribution assets.

---

## 🌟 Key Features

1. **InVideo-Style Web Studio App**:
   - Modern interactive browser studio running on `http://localhost:8000`.
   - **Real-Time Video Player** with synchronized playback and live word-by-word karaoke captions.
   - **Scene & Timeline Storyboard**: Inspect scene timings, edit script text with instant audio re-synthesis, and preview individual scene clips.
   - **Stock Video Search Modal**: Search 5,000,000+ free stock video clips (Pexels, Pixabay, Wikimedia Commons) with live hover-to-play previews and 1-click B-roll replacement.
   - **1-Click 1080p MP4 Export**: Full hardware-accelerated render engine with direct download and viral SEO metadata.
2. **100% Real Moving Video B-Roll (Zero Static Slides)**:
   - Eliminates static text slides completely to prevent platform spam and reuse flags on YouTube and TikTok.
   - Automatically queries **Pexels Video API** and **Pixabay Video API** for 1080p/720p HD MP4 video clips.
   - Integrates **Wikimedia Commons Public Domain Video Archives**.
   - Procedural 30fps cinematic motion video generator (tactile grids, radar sweeps, starfields, oscilloscopes) for guaranteed 100% video footage out-of-the-box.
3. **Dual Aspect Ratio Production**:
   - **16:9 Landscape** (1920x1080) for long-form YouTube documentaries.
   - **9:16 Portrait** (1080x1920) for viral TikTok, YouTube Shorts, and Instagram Reels.
4. **Resilient Neural Voiceover & Millisecond Word Sync**:
   - High-fidelity `edge-tts` Microsoft Neural voices (`en-US-ChristopherNeural`, `en-GB-RyanNeural`, `en-US-JennyNeural`, etc.).
   - Scene-by-scene synthesis ensuring zero dropped scenes and continuous audio across multi-minute scripts.
   - Saves per-scene WAV files enabling instant script tweaks and re-generation in the studio.
5. **Word-by-Word Animated Subtitles**:
   - Generates `.ass` subtitle files with active word pop/highlighting burnt into video via FFmpeg.
   - Built-in styles: **Hormozi** (neon green active pop), **Documentary** (elegant lower-third with golden active word), and **MrBeast** (bold yellow).
6. **Real Video Assembler 2.0**:
   - Automatically scales, center-crops, loops, and splices real MP4 video clips to match scene audio duration.
   - Dynamic music ducking (-18dB under speech with +6dB swells during pauses).
   - Master multi-track audio mixing with cinematic SFX hits (whooshes, deep braams, risers).

---

## 🚀 Quickstart

### 1. Launch the InVideo Web Studio (Recommended)
```powershell
uv run python -m docstudio server
```
Open your browser at **`http://localhost:8000`** to access the interactive studio.

### 2. Run Headless via CLI
```powershell
# 16:9 YouTube Documentary (5-minute in-depth)
uv run python -m docstudio run --topic "The Lost Cosmonaut" --aspect-ratio 16:9 --runtime 5m --style documentary

# 9:16 Viral TikTok / Short (60-second hook with Hormozi captions)
uv run python -m docstudio run --topic "The Dyatlov Pass Mystery" --aspect-ratio 9:16 --runtime 60s --style hormozi
```

---

## 📂 Output & Checkpoints

Every production run creates a dedicated folder in `workspace/runs/<run_id>/`:

| Checkpoint File | Description |
| :--- | :--- |
| `01_script.json` | 7-act structured documentary script and scene cues |
| `02_narration.wav` | Master voiceover audio file |
| `02_word_timestamps.json` | Millisecond-accurate word boundary timestamps |
| `03_captions.ass` | Word-by-word animated subtitle file |
| `04_visuals/` | Downloaded archival/stock photos and generated slides |
| `05_audio_mix.wav` | Mixed master audio (voice + ducked tension bed + SFX) |
| `06_final_render.mp4` | Finished 1080p documentary MP4 video |
| `qc_report.json` / `.md` | Quality Control audit (cadence, dead air, static shots) |
| `distribution_meta.json` / `.md` | 3 High-CTR titles, thumbnail brief, YouTube + Bilibili SEO |

---

## 🔄 Checkpoint Rebuilding

If you edit the script in `01_script.json` or want to change subtitle styles, rebuild only downstream stages without re-synthesizing earlier steps:
```powershell
uv run python -m docstudio run --topic "The Lost Cosmonaut" --force captions,render
```

---

## 🤖 Antigravity Agent Skill

DocStudio is also installed as an IDE agent skill in `.agents/skills/documentary-studio/SKILL.md`. You can instruct your AI assistant in natural language:
> *"Produce a 2-minute documentary video about the Chernobyl liquidators using Ryan's voice and documentary caption style."*

---

## 🎬 Remote Creative Director & V1 Production Engine

DocStudio features a **Remote Creative Director** architecture that replaces keyword heuristics with holistic story direction:
- **Remote AI as Creative Brain**: Determines *what* the viewer sees, *why* they see it, *when* they see it, and *what medium* best communicates the truth.
- **Shot Manifest Contract**: A formal contract (`shot_manifest.json`) specifying scene-by-scene shot directives, exact narration ranges, visual purpose, truth categories, and execution metadata.
- **Centralized Provider & Fallback Registry**: Dispatches directives to specialized providers (route maps, data charts, declassified evidence dossiers, browser video, or curated stock) with semantic fallbacks.
- **Deterministic Asset Caching**: SHA-256 fingerprinting prevents redundant generation and preserves external API quotas.
- **Multi-Point Validation**: Validates timeline coverage, detects shot overlap, enforces truth labeling, and flags visual repetition.
