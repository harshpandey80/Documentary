# DocStudio Bulk Image Generator Chrome Extension

A dedicated Chrome extension built specifically for the **InVideo AI Documentary Studio**. It bridges your real authenticated Google Chrome browser with the DocStudio rendering pipeline, allowing you to bulk-generate documentary visual shots in Meta AI / web generative tools with **zero bot detection** and **automatic asset synchronization**.

---

## Why Use This Custom Extension?

1. **No Bot Detection**: Uses your genuine Google Chrome browser session, active cookies, and login credentials without triggering Cloudflare challenges or bot captchas.
2. **Bulk Multi-Shot Pipeline**: Retrieves the entire storyboard prompt list directly from the DocStudio server (`http://127.0.0.1:8000`), queues all pending cuts, and processes them in batch.
3. **Auto-Sync to Video Assembler**: As each image completes rendering in Meta AI, the extension automatically sends the high-resolution visual directly to `jobs/{job_id}/visuals/synth_{shot_id}.jpg` and updates `assets.json`. The video assembler can immediately animate them with hardware-accelerated Ken Burns motion and burn subtitles!

---

## 🚀 How to Install in Google Chrome (10 Seconds)

1. Open Google Chrome and go to:
   ```
   chrome://extensions
   ```
2. In the top-right corner, turn **ON** **Developer mode** toggle.
3. Click the **Load unpacked** button in the top-left corner.
4. Select the extension directory:
   ```
   c:\Users\Harsh Pandey\OneDrive\Desktop\documentry-AI\extensions\docstudio_bulk_generator
   ```
5. You will see **DocStudio Bulk Image Generator** appear in your extension list and extension toolbar!

---

## 🎬 How to Use

1. Make sure your DocStudio server is running (default `http://127.0.0.1:8000`).
2. Click the **DocStudio** icon in your Chrome extension bar.
3. The popup will automatically connect and display:
   - **Active Project Topic** & total cuts.
   - List of all shots with prompt text and current status (e.g. *Pending AI* vs *Asset Synced*).
4. Click **🚀 Bulk Generate in Meta AI**:
   - The extension opens `https://www.meta.ai/`.
   - A floating **🎬 DocStudio Bulk Bridge** HUD will appear in the bottom-right corner.
   - The bridge enters each prompt (`/imagine ...`), waits for the generated image, syncs it directly into DocStudio, and advances to the next shot!
5. Return to the DocStudio frontend — your generated visuals are already synced into the cut!
