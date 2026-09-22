# DocStudio Pipeline Progress Dashboard

> **Last Updated**: 2026-09-22 14:10:49  
> **Active Run ID**: `antwerp_diamond_heist_short_90s`  
> **Topic**: *The Impossible Antwerp Diamond Heist*  
> **Overall Status**: **RUNNING** (0.0s elapsed)  

---

## 1. Core Checkpoints Status (6 Required Stages)

| Stage | Checkpoint File | Description | Status | File Size |
| :---: | :--- | :--- | :---: | :---: |
| 1 | `01_script.json` | Script & Storyboard Cues | ✅ Exists | 15.5 KB |
| 2 | `02_narration.wav` | Master Voiceover Narration | ✅ Exists | 3.77 MB |
| 3 | `03_captions.ass` | Word-Aligned Subtitles | ✅ Exists | 26.6 KB |
| 4 | `04_visuals` | Visual B-Roll & Manifest | ⏳ Missing / In Progress | N/A |
| 5 | `05_audio_mix.wav` | Ducked Audio Bed & SFX Mix | ⏳ Missing / In Progress | N/A |
| 6 | `06_final_render.mp4` | Composited 1080p Video | ⏳ Missing / In Progress | N/A |

---

## 2. Active Stage Execution Log

| # | Pipeline Stage | Status | Duration | Stage Details |
| :---: | :--- | :---: | :---: | :--- |
| 1 | Script Generation | 🟢 Done | - | Generated 8 acts with performance markup — Claims Gate PASSED |
| 2 | Narration Voiceover (Edge-TTS + Kokoro Failover) | 🟢 Done | - | Synthesized via [cached] (214 word boundaries, 82.5s) |
| 3 | Word-Aligned Subtitle Assembly | 🟢 Done | - | Generated animated .ass subtitles (hormozi style) |
| 4 | B-Roll Visual Acquisition & Color Grade | 🟡 In Progress | - |  |
| 5 | Audio Bed Ducking & SFX Mastering | ⚪ Pending | - |  |
| 6 | FFmpeg Compositing & Burn-in | ⚪ Pending | - |  |
| 7 | Retention QC & Distribution Packaging | ⚪ Pending | - |  |

---

## 3. Quick CLI Commands
```powershell
# Check current active run progress on demand
uv run python -m docstudio status --run-id antwerp_diamond_heist_short_90s

# Check all runs
uv run python -m docstudio status --all
```
