// DocStudio Meta AI Content Bridge
console.log("[DocStudio] Meta AI Bridge script loaded.");

const API_BASE = "http://127.0.0.1:8000";
let isRunning = false;

// Create floating HUD on Meta AI page
function injectHUD() {
  if (document.getElementById("docstudio-hud")) return;

  const hud = document.createElement("div");
  hud.id = "docstudio-hud";
  hud.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 999999;
    background: #11141e;
    color: #e2e8f0;
    border: 1px solid rgba(0, 132, 255, 0.4);
    box-shadow: 0 10px 30px rgba(0,0,0,0.6);
    border-radius: 12px;
    padding: 14px 18px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-width: 280px;
    backdrop-filter: blur(10px);
  `;

  hud.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <div style="display:flex; align-items:center; gap:6px; font-weight:700; color:#fff;">
        <span>🎬</span> DocStudio Bulk Bridge
      </div>
      <span id="ds-status-pill" style="font-size:10px; padding:2px 8px; border-radius:10px; background:rgba(0,132,255,0.2); color:#0084ff; font-weight:600;">
        Ready
      </span>
    </div>
    <div id="ds-prompt-info" style="font-size:11px; color:#94a3b8; line-height:1.4;">
      Waiting to start bulk batch...
    </div>
    <div style="display:flex; gap:8px;">
      <button id="ds-btn-start" style="flex:1; padding:7px 12px; background:#0084ff; color:#fff; border:none; border-radius:6px; font-weight:600; font-size:12px; cursor:pointer;">
        ▶ Process Batch
      </button>
      <button id="ds-btn-minimize" style="padding:7px 10px; background:rgba(255,255,255,0.08); color:#cbd5e1; border:none; border-radius:6px; font-size:11px; cursor:pointer;">
        ✕
      </button>
    </div>
  `;

  document.body.appendChild(hud);

  document.getElementById("ds-btn-start").addEventListener("click", () => {
    if (isRunning) return;
    startBatchGeneration();
  });

  document.getElementById("ds-btn-minimize").addEventListener("click", () => {
    hud.style.display = "none";
  });
}

async function startBatchGeneration() {
  isRunning = true;
  updateHUD("Processing", "Requesting next shot from DocStudio queue...", "#fbbf24");

  chrome.runtime.sendMessage({ action: "GET_NEXT_PROMPT" }, async (resp) => {
    if (!resp || !resp.hasMore) {
      updateHUD("Complete", "All documentary shots synced successfully!", "#10b981");
      isRunning = false;
      return;
    }

    const { shot, jobId, index, total } = resp;
    updateHUD(
      `Cut ${index + 1}/${total}`,
      `Submitting: "${shot.visual_prompt.substring(0, 60)}..."`,
      "#0084ff"
    );

    try {
      await submitPromptToMetaAI(shot.visual_prompt);
      updateHUD(`Cut ${index + 1}/${total}`, "Waiting for Meta AI to render image...", "#a855f7");

      const imageUrl = await waitForNewGeneratedImage();
      if (imageUrl) {
        updateHUD(`Cut ${index + 1}/${total}`, "Syncing image back to DocStudio...", "#06b6d4");
        await uploadVisualToStudio(jobId, shot.shot_id, imageUrl);

        chrome.runtime.sendMessage({ action: "MARK_PROMPT_DONE" }, () => {
          // Pause 3 seconds between generations to allow UI to settle
          setTimeout(() => {
            startBatchGeneration();
          }, 3000);
        });
      } else {
        throw new Error("Timeout waiting for image generation");
      }
    } catch (err) {
      console.error("[DocStudio] Shot generation error:", err);
      updateHUD("Notice", `Notice on cut ${index + 1}: ${err.message}`, "#ef4444");
      isRunning = false;
    }
  });
}

function updateHUD(status, info, color = "#0084ff") {
  const pill = document.getElementById("ds-status-pill");
  const infoEl = document.getElementById("ds-prompt-info");
  if (pill) {
    pill.textContent = status;
    pill.style.color = color;
    pill.style.background = `${color}22`;
  }
  if (infoEl) {
    infoEl.textContent = info;
  }
}

async function submitPromptToMetaAI(promptText) {
  // Find Meta AI input box
  const inputEl = document.querySelector('textarea, div[contenteditable="true"], [aria-label*="Ask Meta AI"], [aria-label*="Message"]');
  if (!inputEl) {
    throw new Error("Could not locate Meta AI message input box");
  }

  const cleanPrompt = promptText.startsWith("/imagine") ? promptText : `/imagine ${promptText}`;

  inputEl.focus();
  if (inputEl.tagName.toLowerCase() === "textarea") {
    inputEl.value = cleanPrompt;
    inputEl.dispatchEvent(new Event("input", { bubbles: true }));
  } else {
    inputEl.innerText = cleanPrompt;
    inputEl.dispatchEvent(new InputEvent("input", { bubbles: true }));
  }

  await sleep(600);

  // Press Enter or click send button
  inputEl.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }));

  const sendBtn = document.querySelector('button[aria-label*="Send"], button[type="submit"]');
  if (sendBtn && !sendBtn.disabled) {
    sendBtn.click();
  }
}

async function waitForNewGeneratedImage(timeoutSeconds = 45) {
  const initialImages = Array.from(document.querySelectorAll("img")).map(img => img.src);
  const startTime = Date.now();

  while ((Date.now() - startTime) < timeoutSeconds * 1000) {
    await sleep(1500);
    const currentImages = Array.from(document.querySelectorAll("img"));
    for (const img of currentImages) {
      const src = img.src || "";
      if (!initialImages.includes(src) && src.startsWith("http") && (img.naturalWidth > 300 || img.width > 300)) {
        return src;
      }
    }
  }
  return null;
}

async function uploadVisualToStudio(jobId, shotId, imageUrl) {
  const payload = {
    job_id: jobId,
    shot_id: shotId,
    image_url: imageUrl
  };

  const resp = await fetch(`${API_BASE}/api/extension/upload_visual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!resp.ok) {
    throw new Error(`Upload failed with status ${resp.status}`);
  }

  return await resp.json();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Initialize HUD on load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", injectHUD);
} else {
  injectHUD();
}
