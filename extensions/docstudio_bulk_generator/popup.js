const API_BASE = "http://127.0.0.1:8000";

let currentJob = null;
let currentShots = [];

document.addEventListener("DOMContentLoaded", () => {
  initPopup();
  setupEventListeners();
});

async function initPopup() {
  const statusEl = document.getElementById("serverStatus");
  const statusText = document.getElementById("statusText");

  try {
    const res = await fetch(`${API_BASE}/api/extension/status`, { cache: "no-cache" });
    if (res.ok) {
      statusEl.className = "server-status";
      statusText.textContent = "Live Connected";
    } else {
      throw new Error("Server error");
    }
  } catch (err) {
    statusEl.className = "server-status offline";
    statusText.textContent = "Studio Offline";
    document.getElementById("shotsList").innerHTML = `
      <div class="empty-state">
        <p style="color:#ef4444; font-weight:600; margin-bottom:6px;">Cannot connect to DocStudio server</p>
        <p>Make sure the studio server is running at <code>http://127.0.0.1:8000</code></p>
      </div>
    `;
    return;
  }

  loadActiveJob();
}

async function loadActiveJob() {
  try {
    const res = await fetch(`${API_BASE}/api/extension/active_prompts`, { cache: "no-cache" });
    const data = await res.json();
    currentJob = data.job_id;
    currentShots = data.shots || [];

    document.getElementById("jobTitle").textContent = data.topic || "Active Documentary Project";
    document.getElementById("shotCount").textContent = `${data.total_shots || 0} cuts`;
    document.getElementById("pendingCount").textContent = `${data.pending_shots || 0} pending`;
    document.getElementById("activeJobId").textContent = data.job_id ? data.job_id.substring(0, 18) + "..." : "";

    renderShots(currentShots);
  } catch (err) {
    console.error("Failed to load prompts:", err);
  }
}

function renderShots(shots) {
  const container = document.getElementById("shotsList");
  if (!shots || shots.length === 0) {
    container.innerHTML = `<div class="empty-state">No storyboard shots found in active project.</div>`;
    return;
  }

  container.innerHTML = "";
  shots.forEach((shot, index) => {
    const card = document.createElement("div");
    card.className = `shot-card ${shot.has_asset ? "done" : ""}`;
    card.id = `shot-${shot.shot_id}`;

    card.innerHTML = `
      <div class="shot-header">
        <span class="shot-badge">Cut #${index + 1} (${shot.shot_id})</span>
        <span class="shot-status">${shot.has_asset ? "✓ Asset Synced" : "Pending AI"}</span>
      </div>
      <div class="shot-prompt">${escapeHtml(shot.visual_prompt)}</div>
      <div class="shot-actions">
        <button class="btn-mini copy" data-prompt="${escapeHtml(shot.visual_prompt)}">Copy Prompt</button>
        <button class="btn-mini single-gen" data-shotid="${shot.shot_id}" data-prompt="${escapeHtml(shot.visual_prompt)}">
          ${shot.has_asset ? "Regenerate" : "Generate in Meta AI"}
        </button>
      </div>
    `;

    card.querySelector(".copy").addEventListener("click", (e) => {
      navigator.clipboard.writeText(shot.visual_prompt);
      const btn = e.target;
      const orig = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = orig; }, 1500);
    });

    card.querySelector(".single-gen").addEventListener("click", () => {
      dispatchPromptsToMetaAI([shot]);
    });

    container.appendChild(card);
  });
}

function setupEventListeners() {
  document.getElementById("btnBulkMetaAI").addEventListener("click", () => {
    const pending = currentShots.filter(s => !s.has_asset);
    const toGenerate = pending.length > 0 ? pending : currentShots;
    if (toGenerate.length === 0) {
      alert("No shots to generate!");
      return;
    }
    dispatchPromptsToMetaAI(toGenerate);
  });

  document.getElementById("btnCopyAll").addEventListener("click", () => {
    if (currentShots.length === 0) return;
    const formatted = currentShots.map((s, idx) => `[Cut ${idx + 1} - ${s.shot_id}]\n${s.visual_prompt}`).join("\n\n");
    navigator.clipboard.writeText(formatted);
    const btn = document.getElementById("btnCopyAll");
    btn.innerHTML = "<span>✓</span> Copied All!";
    setTimeout(() => {
      btn.innerHTML = "<span>📋</span> Copy Prompts";
    }, 2000);
  });
}

function dispatchPromptsToMetaAI(shots) {
  // Send message to background script to launch or focus Meta AI and queue the prompts
  chrome.runtime.sendMessage({
    action: "QUEUE_META_AI_PROMPTS",
    jobId: currentJob,
    shots: shots
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.warn("Background messaging notice:", chrome.runtime.lastError.message);
    }
  });

  // Open or switch to Meta AI
  chrome.tabs.create({ url: "https://www.meta.ai/" });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}
