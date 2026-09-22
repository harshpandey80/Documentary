# DocStudio Pipeline Progress Dashboard

> **Last Updated**: 2026-09-22 14:30:42  
> **Active Run ID**: `antwerp_diamond_heist_short_90s`  
> **Topic**: *The Impossible Antwerp Diamond Heist*  
> **Overall Status**: **COMPLETED** (1193.5s elapsed)  

---

## 1. Core Checkpoints Status (6 Required Stages)

| Stage | Checkpoint File | Description | Status | File Size |
| :---: | :--- | :--- | :---: | :---: |
| 1 | `01_script.json` | Script & Storyboard Cues | ✅ Exists | 15.5 KB |
| 2 | `02_narration.wav` | Master Voiceover Narration | ✅ Exists | 3.77 MB |
| 3 | `03_captions.ass` | Word-Aligned Subtitles | ✅ Exists | 26.6 KB |
| 4 | `04_visuals` | Visual B-Roll & Manifest | ✅ Exists | 55 files |
| 5 | `05_audio_mix.wav` | Ducked Audio Bed & SFX Mix | ✅ Exists | 13.87 MB |
| 6 | `06_final_render.mp4` | Composited 1080p Video | ✅ Exists | 62.85 MB |

---

## 2. Active Stage Execution Log

| # | Pipeline Stage | Status | Duration | Stage Details |
| :---: | :--- | :---: | :---: | :--- |
| 1 | Script Generation | 🟢 Done | - | Generated 8 acts with performance markup — Claims Gate PASSED |
| 2 | Narration Voiceover (Edge-TTS + Kokoro Failover) | 🟢 Done | - | Synthesized via [cached] (214 word boundaries, 82.5s) |
| 3 | Word-Aligned Subtitle Assembly | 🟢 Done | - | Generated animated .ass subtitles (hormozi style) |
| 4 | B-Roll Visual Acquisition & Color Grade | 🟢 Done | 1087.64s | Acquired 39 visual assets with verified license manifest and contact sheet |
| 5 | Audio Bed Ducking & SFX Mastering | 🟢 Done | 4.45s | Master audio normalized to -14 LUFS (dynamic ducking & SFX) |
| 6 | FFmpeg Compositing & Burn-in | 🟢 Done | 100.45s | Composited 1080p video with color grade & 35mm grain (FCPXML 1.8 validated & exported) |
| 7 | Retention QC & Distribution Packaging | 🟢 Done | 0.01s | QC Status: REVIEW_RECOMMENDED (Score: 75/100) |

---

## 3. Quick CLI Commands
```powershell
# Check current active run progress on demand
uv run python -m docstudio status --run-id antwerp_diamond_heist_short_90s

# Check all runs
uv run python -m docstudio status --all
```
