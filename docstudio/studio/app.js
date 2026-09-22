// InVideo AI Documentary Studio Client Application
let currentProject = null;
let currentRunId = null;
let currentJobId = null;
let targetReplaceSceneId = null;
let currentAspectRatio = "16:9";
let wordTimestamps = [];

// DOM Elements
const studioVideo = document.getElementById("studioVideo");
const playerWrapper = document.getElementById("playerWrapper");
const captionText = document.getElementById("captionText");
const captionOverlay = document.getElementById("captionOverlay");
const playerSceneBadge = document.getElementById("playerSceneBadge");
const videoScrubber = document.getElementById("videoScrubber");
const btnPlayPause = document.getElementById("btnPlayPause");
const playIcon = document.getElementById("playIcon");
const pauseIcon = document.getElementById("pauseIcon");
const timecodeDisplay = document.getElementById("timecodeDisplay");
const scenesList = document.getElementById("scenesList");
const sceneCountBadge = document.getElementById("sceneCountBadge");
const activeProjectTitle = document.getElementById("activeProjectTitle");
const progressBanner = document.getElementById("progressBanner");
const progressBarFill = document.getElementById("progressBarFill");
const progressStatusText = document.getElementById("progressStatusText");

// Stepper Elements
const stepperJobTitle = document.getElementById("stepperJobTitle");
const stepperJobStatus = document.getElementById("stepperJobStatus");
const btnInspectArtifacts = document.getElementById("btnInspectArtifacts");
const btnExportResolveNav = document.getElementById("btnExportResolveNav");
const artifactModal = document.getElementById("artifactModal");
const btnCloseArtifactModal = document.getElementById("btnCloseArtifactModal");
const artifactContentDisplay = document.getElementById("artifactContentDisplay");
const artifactLoadedTitle = document.getElementById("artifactLoadedTitle");
const btnCopyArtifact = document.getElementById("btnCopyArtifact");

// Modals
const stockModal = document.getElementById("stockModal");
const btnCloseStockModal = document.getElementById("btnCloseStockModal");
const stockSearchInput = document.getElementById("stockSearchInput");
const btnExecStockSearch = document.getElementById("btnExecStockSearch");
const stockResultsGrid = document.getElementById("stockResultsGrid");
const stockLoading = document.getElementById("stockLoading");
const customVideoUpload = document.getElementById("customVideoUpload");

const projectsModal = document.getElementById("projectsModal");
const btnCloseProjectsModal = document.getElementById("btnCloseProjectsModal");
const projectsListGrid = document.getElementById("projectsListGrid");
const btnProjectsList = document.getElementById("btnProjectsList");

const renderModal = document.getElementById("renderModal");
const btnCloseRenderModal = document.getElementById("btnCloseRenderModal");
const btnRenderProject = document.getElementById("btnRenderProject");
const btnStartFullRender = document.getElementById("btnStartFullRender");
const btnDownloadFinal = document.getElementById("btnDownloadFinal");
const btnDownloadTop = document.getElementById("btnDownloadTop");
const seoBox = document.getElementById("seoBox");
const seoTitles = document.getElementById("seoTitles");

function setDownloadButtons(downloadUrl, filename) {
  const finalBtn = document.getElementById("btnDownloadFinal");
  const topBtn = document.getElementById("btnDownloadTop");
  const name = filename || "documentary.mp4";

  [finalBtn, topBtn].forEach(btn => {
    if (!btn) return;
    if (downloadUrl) {
      btn.classList.remove("hidden");
      btn.href = downloadUrl;
      btn.setAttribute("download", name);
      btn.style.display = "inline-flex";
    } else {
      btn.classList.add("hidden");
      btn.style.display = "none";
      btn.href = "#";
    }
  });
}

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadLatestJobOrProject();
});

function initEventListeners() {
  // Aspect Ratio Toggle
  document.getElementById("btnAspect169").addEventListener("click", () => setAspectRatio("16:9"));
  document.getElementById("btnAspect916").addEventListener("click", () => setAspectRatio("9:16"));

  // Autonomous Pipeline Generation
  document.getElementById("btnGenerate").addEventListener("click", handleGenerate);
  document.getElementById("promptInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") handleGenerate();
  });

  // Artifact Inspector & Resolve Export
  if (btnInspectArtifacts) {
    btnInspectArtifacts.addEventListener("click", () => openArtifactModal("research.json"));
  }
  if (btnCloseArtifactModal) {
    btnCloseArtifactModal.addEventListener("click", () => artifactModal.classList.add("hidden"));
  }
  if (btnCopyArtifact) {
    btnCopyArtifact.addEventListener("click", () => {
      navigator.clipboard.writeText(artifactContentDisplay.textContent || "").then(() => {
        btnCopyArtifact.textContent = "✅ Copied!";
        setTimeout(() => { btnCopyArtifact.textContent = "📋 Copy JSON"; }, 1500);
      });
    });
  }
  if (btnExportResolveNav) {
    btnExportResolveNav.addEventListener("click", handleExportResolve);
  }

  // Stepper Node Clicks
  document.querySelectorAll(".step-node").forEach(node => {
    node.addEventListener("click", () => {
      const stage = node.dataset.stage;
      const artifactMap = {
        research: "research.json",
        claims: "claims.json",
        story: "story.json",
        narration: "narration.json",
        storyboard: "storyboard.json",
        assets: "assets.json",
        graphics: "graphics.json",
        audio: "audio.json",
        rendering: "timeline.json",
        qc: "qc.json",
      };
      if (artifactMap[stage]) {
        openArtifactModal(artifactMap[stage]);
      }
    });
  });

  // Tab switcher in Artifact Modal
  document.querySelectorAll("#artifactTabBar .tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#artifactTabBar .tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const art = btn.dataset.artifact;
      if (art) loadArtifactContent(art);
    });
  });

  // Video Playback Controls
  btnPlayPause.addEventListener("click", togglePlayPause);
  studioVideo.addEventListener("click", togglePlayPause);
  studioVideo.addEventListener("timeupdate", handleTimeUpdate);
  studioVideo.addEventListener("ended", () => {
    playIcon.classList.remove("hidden");
    pauseIcon.classList.add("hidden");
  });

  videoScrubber.addEventListener("input", (e) => {
    const time = (e.target.value / 100) * (studioVideo.duration || 1);
    studioVideo.currentTime = time;
  });

  document.getElementById("btnFullscreen").addEventListener("click", () => {
    if (!document.fullscreenElement) {
      playerWrapper.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  });

  // Stock Video Search & Gemini Modal Tabs
  const tabStockSearch = document.getElementById("tabStockSearch");
  const tabGeminiAI = document.getElementById("tabGeminiAI");
  const sectionStockSearch = document.getElementById("sectionStockSearch");
  const sectionGeminiAI = document.getElementById("sectionGeminiAI");

  if (tabStockSearch && tabGeminiAI) {
    const tabVimaxClip = document.getElementById('tabVimaxClip');
    const sectionVimaxClip = document.getElementById('sectionVimaxClip');
    const allTabs = [tabStockSearch, tabGeminiAI, tabVimaxClip].filter(Boolean);
    const allSections = [sectionStockSearch, sectionGeminiAI, sectionVimaxClip].filter(Boolean);

    function activateTab(activeTab, activeSection) {
      allTabs.forEach(t => {
        t.classList.remove('active');
        t.style.background = '';
        t.style.color = '';
      });
      allSections.forEach(s => s.classList.add('hidden'));
      activeTab.classList.add('active');
      activeTab.style.background = '';
      activeTab.style.color = '';
      activeSection.classList.remove('hidden');
    }

    tabStockSearch.addEventListener('click', () => activateTab(tabStockSearch, sectionStockSearch));
    tabGeminiAI.addEventListener('click', () => activateTab(tabGeminiAI, sectionGeminiAI));
    if (tabVimaxClip) {
      tabVimaxClip.addEventListener('click', () => activateTab(tabVimaxClip, sectionVimaxClip));
    }
  }

  const btnExecGeminiGenerate = document.getElementById("btnExecGeminiGenerate");
  if (btnExecGeminiGenerate) {
    btnExecGeminiGenerate.addEventListener("click", handleGeminiGenerate);
  }

  document.getElementById("btnSearchStockNav").addEventListener("click", () => openStockModal(null));
  btnCloseStockModal.addEventListener("click", () => stockModal.classList.add("hidden"));
  btnExecStockSearch.addEventListener("click", () => execStockSearch(stockSearchInput.value));
  stockSearchInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") execStockSearch(stockSearchInput.value);
  });

  document.querySelectorAll(".stock-category-pills .pill").forEach(btn => {
    btn.addEventListener("click", () => {
      stockSearchInput.value = btn.dataset.cat;
      execStockSearch(btn.dataset.cat);
    });
  });

  customVideoUpload.addEventListener("change", handleCustomVideoUpload);

  // Projects Switcher Modal
  btnProjectsList.addEventListener("click", openProjectsModal);
  btnCloseProjectsModal.addEventListener("click", () => projectsModal.classList.add("hidden"));

  // Render Modal
  btnRenderProject.addEventListener('click', openRenderModal);
  btnCloseRenderModal.addEventListener('click', () => renderModal.classList.add('hidden'));
  btnStartFullRender.addEventListener('click', triggerFinalRender);

  // Dubbing Panel
  const btnStartDubbing = document.getElementById('btnStartDubbing');
  if (btnStartDubbing) {
    btnStartDubbing.addEventListener('click', handleStartDubbing);
  }

  // ViMax AI Clip
  const btnExecVimaxClip = document.getElementById('btnExecVimaxClip');
  if (btnExecVimaxClip) {
    btnExecVimaxClip.addEventListener('click', handleVimaxClipGenerate);
  }

  // Robust Download Handlers
  const handleDownloadClick = (e, btn) => {
    const href = btn.getAttribute("href");
    if (!href || href === "#" || href.endsWith("#")) {
      e.preventDefault();
      const targetUrl = currentJobId
        ? `/api/documentary/jobs/${currentJobId}/download`
        : (currentRunId ? `/api/project/${currentRunId}/download` : (studioVideo && studioVideo.src));
      if (targetUrl) {
        window.location.href = targetUrl;
      } else {
        alert("Video is still generating or not available yet.");
      }
    }
  };

  if (btnDownloadFinal) {
    btnDownloadFinal.addEventListener("click", (e) => handleDownloadClick(e, btnDownloadFinal));
  }
  if (btnDownloadTop) {
    btnDownloadTop.addEventListener("click", (e) => handleDownloadClick(e, btnDownloadTop));
  }
}

function setAspectRatio(ratio) {
  currentAspectRatio = ratio;
  document.getElementById("btnAspect169").classList.toggle("active", ratio === "16:9");
  document.getElementById("btnAspect916").classList.toggle("active", ratio === "9:16");

  playerWrapper.classList.toggle("aspect-16-9", ratio === "16:9");
  playerWrapper.classList.toggle("aspect-9-16", ratio === "9:16");

  document.getElementById("metaRes").textContent = ratio === "16:9" ? "1920x1080 (16:9 FHD)" : "1080x1920 (9:16 Vertical)";
}

async function loadLatestProject() {
  try {
    const res = await fetch("/api/projects");
    const projects = await res.json();
    if (projects && projects.length > 0) {
      loadProject(projects[0].id);
    }
  } catch (err) {
    console.warn("Could not load projects:", err);
  }
}

async function loadProject(runId) {
  try {
    const res = await fetch(`/api/project/${runId}`);
    if (!res.ok) return;
    const data = await res.json();
    currentProject = data;
    currentRunId = runId;

    activeProjectTitle.textContent = data.topic || runId;
    wordTimestamps = data.word_timestamps || [];

    // Set Video Source
    if (data.video_url) {
      studioVideo.src = data.video_url;
      studioVideo.load();
    } else if (data.scenes && data.scenes.length > 0 && data.scenes[0].visual_url) {
      studioVideo.src = data.scenes[0].visual_url;
      studioVideo.load();
    }

    if (data.has_final_video || data.video_url) {
      setDownloadButtons(`/api/project/${runId}/download`, `${runId}.mp4`);
    } else {
      setDownloadButtons(null);
    }

    renderScenesList(data.scenes || []);
  } catch (err) {
    console.error("Error loading project:", err);
  }
}

function renderScenesList(scenes) {
  scenesList.innerHTML = "";
  sceneCountBadge.textContent = `${scenes.length} Scenes`;

  if (scenes.length === 0) {
    scenesList.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🎬</div>
        <h4>No Scenes in Project</h4>
      </div>
    `;
    return;
  }

  scenes.forEach((sc, idx) => {
    const card = document.createElement("div");
    card.className = "scene-card";
    card.id = `sceneCard_${sc.scene_id}`;

    const isVideo = sc.visual_url && sc.visual_url.endsWith(".mp4");
    const thumbHtml = isVideo
      ? `<video src="${sc.visual_url}" muted preload="metadata"></video>`
      : (sc.visual_url ? `<img src="${sc.visual_url}" alt="Scene B-Roll" />` : `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#6b7280;font-size:0.75rem;">No Clip</div>`);

    card.innerHTML = `
      <div class="scene-card-top">
        <div class="scene-badge-info">
          <span class="scene-id-tag">ACT ${sc.act_number} · S${idx+1}</span>
          <span class="scene-intensity-tag">★ Intensity: ${sc.intensity}/10</span>
        </div>
        <button class="btn btn-sm btn-outline btn-preview-scene" data-scid="${sc.scene_id}" data-url="${sc.visual_url}">
          ▶ Preview
        </button>
      </div>

      <div class="scene-card-body">
        <div class="scene-thumb-preview" title="Click to replace B-Roll footage">
          ${thumbHtml}
          <div class="thumb-overlay-play">🔁</div>
        </div>

        <div class="scene-script-edit">
          <textarea class="scene-script-text" rows="2" data-scid="${sc.scene_id}">${sc.narration}</textarea>
        </div>
      </div>

      <div class="scene-actions">
        <button class="btn btn-sm btn-secondary btn-replace-broll" data-scid="${sc.scene_id}" data-kw="${(sc.broll_keywords || []).join(', ')}">
          🔁 Replace B-Roll
        </button>
        <button class="btn btn-sm btn-outline btn-regen-voice" data-scid="${sc.scene_id}">
          🎙️ Save & Regen Voice
        </button>
      </div>
    `;

    // Click thumbnail or Replace button to open Stock Modal
    card.querySelector(".scene-thumb-preview").addEventListener("click", () => openStockModal(sc.scene_id, sc.broll_keywords, sc.visual_prompt));
    card.querySelector(".btn-replace-broll").addEventListener("click", () => openStockModal(sc.scene_id, sc.broll_keywords, sc.visual_prompt));

    // Preview scene clip
    card.querySelector(".btn-preview-scene").addEventListener("click", () => {
      if (sc.visual_url) {
        studioVideo.src = sc.visual_url;
        studioVideo.play();
        playerSceneBadge.textContent = `ACT ${sc.act_number} · SCENE ${idx+1}`;
      }
    });

    // Save & Re-synthesize voice
    card.querySelector(".btn-regen-voice").addEventListener("click", async () => {
      const textarea = card.querySelector(".scene-script-text");
      await saveSceneScript(sc.scene_id, textarea.value);
    });

    scenesList.appendChild(card);
  });
}

// Live Video Time & Karaoke Subtitle Sync
function handleTimeUpdate() {
  if (!studioVideo.duration) return;
  const current = studioVideo.currentTime;
  const total = studioVideo.duration;

  // Scrubber sync
  videoScrubber.value = (current / total) * 100;
  timecodeDisplay.textContent = `${formatTime(current)} / ${formatTime(total)}`;

  // Word-by-word active caption highlight
  if (wordTimestamps && wordTimestamps.length > 0) {
    const activeIdx = wordTimestamps.findIndex(w => current >= w.start && current <= w.end);
    if (activeIdx !== -1) {
      // Show window of 4-5 words with active word highlighted
      const startWindow = Math.max(0, activeIdx - 2);
      const endWindow = Math.min(wordTimestamps.length, activeIdx + 3);
      const windowWords = wordTimestamps.slice(startWindow, endWindow);

      const html = windowWords.map((w, i) => {
        const isCurrent = (startWindow + i) === activeIdx;
        return `<span class="${isCurrent ? 'word-active' : ''}">${w.word}</span>`;
      }).join(" ");

      captionText.innerHTML = html;
      captionOverlay.classList.remove("hidden");
    }
  }
}

function togglePlayPause() {
  if (studioVideo.paused) {
    studioVideo.play();
    playIcon.classList.add("hidden");
    pauseIcon.classList.remove("hidden");
  } else {
    studioVideo.pause();
    playIcon.classList.remove("hidden");
    pauseIcon.classList.add("hidden");
  }
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// Autonomous Documentary Generation Handler (Autonomous Rules 1, 2, 27)
async function handleGenerate() {
  const prompt = document.getElementById('promptInput').value.trim();
  if (!prompt) return;

  const runtimeStr = document.getElementById('selectRuntime').value;
  let durationSec = 60.0;
  if (runtimeStr === "3m") durationSec = 180.0;
  else if (runtimeStr === "5m") durationSec = 300.0;
  else if (runtimeStr === "8m") durationSec = 480.0;
  else if (runtimeStr === "60s") durationSec = 60.0;

  const voice = document.getElementById('selectVoice').value;
  const captionStyle = document.getElementById('selectCaptionStyle').value;
  const style = document.getElementById('selectStyle')?.value || "cinematic_investigative";
  const researchDepth = document.getElementById('selectResearchDepth')?.value || "deep";

  // Reset stepper nodes
  resetStepperTrack();
  stepperJobTitle.textContent = prompt;
  stepperJobStatus.textContent = "RESEARCHING";
  progressStatusText.textContent = "🚀 Starting autonomous documentary pipeline...";
  progressBarFill.style.width = "5%";

  try {
    const payload = {
      topic: prompt,
      duration_target: durationSec,
      format: currentAspectRatio === "9:16" ? "shorts" : "youtube",
      aspect_ratio: currentAspectRatio,
      style: style,
      research_depth: researchDepth,
      voice: voice,
      caption_style: captionStyle,
    };

    const res = await fetch('/api/documentary/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    currentJobId = data.job_id;
    currentRunId = data.job_id;
    activeProjectTitle.textContent = prompt;

    pollAutonomousJob(data.job_id);
  } catch (err) {
    alert('Autonomous generation request failed: ' + err);
    stepperJobStatus.textContent = "FAILED";
  }
}

function resetStepperTrack() {
  document.querySelectorAll(".step-node").forEach(node => {
    node.classList.remove("active", "done", "failed");
  });
  document.querySelectorAll(".step-line").forEach(line => {
    line.classList.remove("done");
  });
}

function pollAutonomousJob(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/documentary/jobs/${jobId}`);
      if (!res.ok) return;
      const job = await res.json();

      progressBarFill.style.width = `${job.progress_percent || 10}%`;
      stepperJobStatus.textContent = (job.status || "RUNNING").toUpperCase();

      // Update individual stage nodes
      const stages = job.stages || {};
      const stageSequence = ["research", "claims", "story", "narration", "storyboard", "assets", "graphics", "audio", "rendering", "qc"];
      
      stageSequence.forEach((stName, idx) => {
        const node = document.querySelector(`.step-node[data-stage="${stName}"]`);
        const stInfo = stages[stName];
        if (node && stInfo) {
          node.classList.remove("active", "done", "failed");
          if (stInfo.status === "done") {
            node.classList.add("done");
            const nextLine = node.nextElementSibling;
            if (nextLine && nextLine.classList.contains("step-line")) {
              nextLine.classList.add("done");
            }
          } else if (stInfo.status === "in_progress") {
            node.classList.add("active");
            if (stInfo.details) {
              progressStatusText.textContent = `[${stInfo.name}] ${stInfo.details}`;
            }
          } else if (stInfo.status === "failed") {
            node.classList.add("failed");
          }
        }
      });

      if (job.status === "completed") {
        clearInterval(interval);
        progressBarFill.style.width = "100%";
        stepperJobStatus.textContent = "COMPLETED";
        progressStatusText.textContent = `✅ Autonomous documentary production complete! (${job.summary?.runtime_seconds || ''}s)`;

        // Load final video into player
        if (job.video_url) {
          studioVideo.src = job.video_url;
          studioVideo.load();
        }

        setDownloadButtons(`/api/documentary/jobs/${jobId}/download`, `${jobId}.mp4`);

        // Load storyboard scenes into editor
        loadJobStoryboard(jobId);
      } else if (job.status === "failed") {
        clearInterval(interval);
        stepperJobStatus.textContent = "FAILED";
        progressStatusText.textContent = `❌ Production stopped: ${job.error || "Stage failed"}`;
      }
    } catch (e) {
      console.warn("Job poll error:", e);
    }
  }, 2000);
}

async function loadJobStoryboard(jobId) {
  try {
    const res = await fetch(`/api/documentary/jobs/${jobId}/artifact/storyboard.json`);
    if (!res.ok) return;
    const sb = await res.json();
    const scList = (sb.scenes || []).map((sc, i) => {
      const firstShot = (sc.shots && sc.shots[0]) || {};
      let visualUrl = firstShot.asset_path || "";
      if (visualUrl && (visualUrl.includes("jobs\\") || visualUrl.includes("jobs/"))) {
        const norm = visualUrl.replace(/\\/g, "/");
        const jIndex = norm.lastIndexOf("/jobs/");
        if (jIndex !== -1) {
          visualUrl = `/media/jobs/${norm.substring(jIndex + 6)}`;
        }
      }
      return {
        scene_id: sc.scene_id || `s_${i+1}`,
        act_number: Math.floor(i / 3) + 1,
        act_name: sc.story_beat || "",
        narration: sc.narration || "",
        intensity: firstShot.intensity || 5,
        visual_prompt: firstShot.visual_prompt || "",
        broll_keywords: firstShot.broll_keywords || [],
        motion: firstShot.motion || "zoom_in",
        visual_url: visualUrl,
        audio_url: "",
      };
    });
    renderScenesList(scList);
  } catch (err) {
    console.info("Notice: Could not load storyboard artifact:", err);
  }
}

async function loadLatestJobOrProject() {
  try {
    const res = await fetch('/api/documentary/jobs');
    const jobs = await res.json();
    if (jobs && jobs.length > 0) {
      const latest = jobs[0];
      currentJobId = latest.job_id;
      stepperJobTitle.textContent = latest.topic || latest.job_id;
      stepperJobStatus.textContent = (latest.status || "IDLE").toUpperCase();
      if (latest.has_video && latest.video_url) {
        studioVideo.src = latest.video_url;
        studioVideo.load();
        setDownloadButtons(`/api/documentary/jobs/${latest.job_id}/download`, `${latest.job_id}.mp4`);
      }
      loadJobStoryboard(latest.job_id);
      return;
    }
  } catch (e) {
    console.info("Notice: No previous jobs:", e);
  }
  loadLatestProject();
}

async function openArtifactModal(artifactName) {
  if (!currentJobId) {
    alert("Please initiate or select a documentary job to inspect artifacts.");
    return;
  }
  artifactModal.classList.remove("hidden");
  document.getElementById("artifactJobSubtitle").textContent = `Job: ${currentJobId}`;
  
  // Highlight active tab
  document.querySelectorAll("#artifactTabBar .tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.artifact === artifactName);
  });
  loadArtifactContent(artifactName);
}

async function loadArtifactContent(artifactName) {
  artifactLoadedTitle.textContent = `Viewing: ${artifactName}`;
  artifactContentDisplay.textContent = "Loading artifact...";

  try {
    const res = await fetch(`/api/documentary/jobs/${currentJobId}/artifact/${artifactName}`);
    if (!res.ok) {
      artifactContentDisplay.textContent = `Artifact '${artifactName}' is pending or not yet generated in current pipeline run.`;
      return;
    }
    const data = await res.json();
    artifactContentDisplay.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    artifactContentDisplay.textContent = `Error loading artifact: ${e}`;
  }
}

async function handleExportResolve() {
  if (!currentJobId) {
    alert("No completed job selected. Please generate a documentary first.");
    return;
  }
  try {
    const res = await fetch(`/api/documentary/jobs/${currentJobId}/export-resolve`, { method: "POST" });
    const data = await res.json();
    if (data.fcpxml_url) {
      window.open(data.fcpxml_url, "_blank");
    }
    alert(`🎬 DaVinci Resolve Integration:\n${JSON.stringify(data.resolve_result || data, null, 2)}`);
  } catch (e) {
    alert(`Resolve export error: ${e}`);
  }
}

// Stock Video Search & Gemini Modal
function openStockModal(sceneId, keywords, visualPrompt) {
  targetReplaceSceneId = sceneId;
  stockModal.classList.remove("hidden");

  let initialQuery = "cinematic documentary";
  if (keywords && keywords.length > 0) {
    initialQuery = keywords.join(" ");
  } else if (currentProject && currentProject.topic) {
    initialQuery = currentProject.topic;
  }

  stockSearchInput.value = initialQuery;
  execStockSearch(initialQuery);

  const geminiInput = document.getElementById("geminiPromptInput");
  if (geminiInput) {
    geminiInput.value = visualPrompt || initialQuery;
  }
}

async function handleGeminiGenerate() {
  const promptInput = document.getElementById("geminiPromptInput");
  const prompt = promptInput ? promptInput.value.trim() : "";
  if (!prompt || !targetReplaceSceneId || !currentRunId) {
    alert("Please enter a scene visual description for Gemini AI.");
    return;
  }

  const statusEl = document.getElementById("geminiGeneratingStatus");
  const btn = document.getElementById("btnExecGeminiGenerate");
  if (statusEl) statusEl.classList.remove("hidden");
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Synthesizing...";
  }

  try {
    const formData = new FormData();
    formData.append("prompt", prompt);

    const res = await fetch(`/api/project/${currentRunId}/scene/${targetReplaceSceneId}/generate-gemini-visual`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (res.ok) {
      stockModal.classList.add("hidden");
      await loadProject(currentRunId);
    } else {
      alert("Gemini generation failed: " + (data.detail || "Error"));
    }
  } catch (err) {
    alert("Gemini generation error: " + err);
  } finally {
    if (statusEl) statusEl.classList.add("hidden");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Generate & Apply Visual";
    }
  }
}

async function execStockSearch(query) {
  if (!query) return;
  stockResultsGrid.innerHTML = "";
  stockLoading.classList.remove("hidden");

  try {
    const orientation = currentAspectRatio === "9:16" ? "portrait" : "landscape";
    const res = await fetch(`/api/search-stock-videos?query=${encodeURIComponent(query)}&orientation=${orientation}&count=9`);
    const data = await res.json();
    stockLoading.classList.add("hidden");

    if (!data.results || data.results.length === 0) {
      stockResultsGrid.innerHTML = `<p style="grid-column:1/-1;text-align:center;color:#9ca3af;">No stock video clips found. Try another search term!</p>`;
      return;
    }

    data.results.forEach(v => {
      const card = document.createElement("div");
      card.className = "stock-card";
      card.innerHTML = `
        <video class="stock-card-thumb" src="${v.preview_url}" muted loop playsinline onmouseover="this.play()" onmouseout="this.pause()"></video>
        <div class="stock-card-info">
          <span class="stock-card-title">${v.title}</span>
          <span class="stock-card-meta">${v.source} · ${v.width}x${v.height} · ${v.duration}s</span>
        </div>
      `;
      card.addEventListener("click", () => applyStockVideoToScene(v.download_url));
      stockResultsGrid.appendChild(card);
    });
  } catch (err) {
    stockLoading.classList.add("hidden");
    console.error("Stock search error:", err);
  }
}

async function applyStockVideoToScene(videoUrl) {
  if (!targetReplaceSceneId || !currentRunId) return;

  try {
    const formData = new FormData();
    formData.append("video_url", videoUrl);

    const res = await fetch(`/api/project/${currentRunId}/scene/${targetReplaceSceneId}/replace-video`, {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      stockModal.classList.add("hidden");
      await loadProject(currentRunId);
    }
  } catch (err) {
    alert("Failed to replace scene video: " + err);
  }
}

async function handleCustomVideoUpload(e) {
  const file = e.target.files[0];
  if (!file || !targetReplaceSceneId || !currentRunId) return;

  const formData = new FormData();
  formData.append("upload_file", file);

  try {
    const res = await fetch(`/api/project/${currentRunId}/scene/${targetReplaceSceneId}/replace-video`, {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      stockModal.classList.add("hidden");
      await loadProject(currentRunId);
    }
  } catch (err) {
    alert("Upload failed: " + err);
  }
}

async function saveSceneScript(sceneId, narration) {
  if (!currentRunId) return;
  try {
    const formData = new FormData();
    formData.append("narration", narration);

    const res = await fetch(`/api/project/${currentRunId}/scene/${sceneId}/edit-script`, {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      const data = await res.json();
      // Play new audio
      if (data.audio_url) {
        const audio = new Audio(data.audio_url);
        audio.play();
      }
    }
  } catch (err) {
    alert("Error updating script: " + err);
  }
}

// Projects Switcher Modal
async function openProjectsModal() {
  projectsModal.classList.remove("hidden");
  projectsListGrid.innerHTML = `<p>Loading projects...</p>`;

  try {
    const res = await fetch("/api/projects");
    const projects = await res.json();
    projectsListGrid.innerHTML = "";

    projects.forEach(p => {
      const item = document.createElement("div");
      item.className = "scene-card";
      item.style.cursor = "pointer";
      const isReady = p.has_video;
      item.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,0.06);display:flex;align-items:center;justify-content:center;font-size:1rem;">🎬</div>
            <div>
              <h4 style="font-size:0.9rem;font-weight:700;color:#fff;margin-bottom:2px;">${p.title}</h4>
              <p style="font-size:0.75rem;color:var(--text-secondary);">${p.duration.toFixed(1)}s runtime · ${isReady ? '1080p MP4 Ready' : 'In Progress'}</p>
            </div>
          </div>
          <span class="badge-studio" style="${isReady ? 'color:var(--accent-neon);border-color:rgba(16,185,129,0.3);background:rgba(16,185,129,0.1);' : ''}">${p.status.toUpperCase()}</span>
        </div>
      `;
      item.addEventListener("click", () => {
        loadProject(p.id);
        projectsModal.classList.add("hidden");
      });
      projectsListGrid.appendChild(item);
    });
  } catch (e) {
    projectsListGrid.innerHTML = `<p>Error loading projects</p>`;
  }
}

// Render & Export Modal
function openRenderModal() {
  if (!currentProject) return;
  renderModal.classList.remove("hidden");
  document.getElementById("renderTopicTitle").textContent = currentProject.topic;

  if (currentProject.has_final_video) {
    setDownloadButtons(`/api/project/${currentRunId}/download`, `${currentRunId}.mp4`);
  } else {
    setDownloadButtons(null);
  }

  // Populate SEO distribution
  if (currentProject.distribution && currentProject.distribution.youtube_seo) {
    seoBox.classList.remove('hidden');
    const yt = currentProject.distribution.youtube_seo;
    const titles = yt.high_ctr_titles || [];
    seoTitles.innerHTML = titles.map(t => `<div style="padding:6px;background:rgba(255,255,255,0.05);border-radius:4px;margin-bottom:4px;font-weight:600;">📌 ${t}</div>`).join('');
  }

  // Show dubbing panel when video exists
  const dubPanel = document.getElementById('dubPanel');
  if (dubPanel) {
    if (currentProject.has_final_video) {
      dubPanel.classList.remove('hidden');
    } else {
      dubPanel.classList.add('hidden');
    }
  }
}

async function triggerFinalRender() {
  if (!currentRunId) return;
  btnStartFullRender.textContent = "Rendering in Progress...";
  btnStartFullRender.disabled = true;

  try {
    const formData = new FormData();
    formData.append("caption_style", document.getElementById("selectCaptionStyle").value);

    await fetch(`/api/project/${currentRunId}/render`, {
      method: "POST",
      body: formData,
    });

    // Check completion
    const checkInterval = setInterval(async () => {
      const res = await fetch(`/api/project/${currentRunId}`);
      const data = await res.json();
      if (data.has_final_video) {
        clearInterval(checkInterval);
        btnStartFullRender.textContent = "Render Completed!";
        setDownloadButtons(`/api/project/${currentRunId}/download`, `${currentRunId}.mp4`);
        studioVideo.src = data.video_url;
        studioVideo.load();
      }
    }, 3000);
  } catch (err) {
    alert('Render error: ' + err);
    btnStartFullRender.textContent = 'Start Final Render';
    btnStartFullRender.disabled = false;
  }
}

// ======================================================
// Dubbing Handler (pyvideotrans engine)
// ======================================================
async function handleStartDubbing() {
  if (!currentRunId) return alert('No active project. Generate a video first.');

  const lang = document.getElementById('dubLanguageSelect').value;
  const burnSubs = document.getElementById('dubBurnSubtitles').checked;
  const statusArea = document.getElementById('dubStatusArea');
  const statusText = document.getElementById('dubStatusText');
  const downloadArea = document.getElementById('dubDownloadArea');
  const btnStartDubbing = document.getElementById('btnStartDubbing');

  statusArea.classList.remove('hidden');
  downloadArea.classList.add('hidden');
  btnStartDubbing.disabled = true;
  statusText.textContent = `Transcribing & translating to ${lang}...`;

  try {
    const formData = new FormData();
    formData.append('target_language', lang);
    formData.append('burn_subtitles', burnSubs ? 'true' : 'false');

    const res = await fetch(`/api/project/${currentRunId}/dub`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      statusText.textContent = 'Dubbing failed: ' + (data.detail || 'Unknown error');
      return;
    }

    // Poll dub status
    const pollDub = setInterval(async () => {
      try {
        const sr = await fetch(`/api/project/${currentRunId}/dub/status`);
        const sd = await sr.json();
        const task = sd.task;
        statusText.textContent = task.message || 'Dubbing in progress...';

        if (task.status === 'completed') {
          clearInterval(pollDub);
          statusArea.classList.add('hidden');
          downloadArea.classList.remove('hidden');
          const dubbed = sd.dubbed_versions.find(v => v.language === lang);
          if (dubbed) {
            document.getElementById('btnDownloadDubbed').href = dubbed.url;
          }
          btnStartDubbing.disabled = false;
        } else if (task.status === 'error') {
          clearInterval(pollDub);
          statusText.textContent = '❌ Dubbing error: ' + task.message;
          btnStartDubbing.disabled = false;
        }
      } catch (e) {}
    }, 3000);
  } catch (err) {
    statusText.textContent = 'Dubbing failed: ' + err;
    btnStartDubbing.disabled = false;
  }
}

// ======================================================
// ViMax AI Cinematic Clip Generator Handler
// ======================================================
async function handleVimaxClipGenerate() {
  if (!targetReplaceSceneId || !currentRunId) {
    return alert('Open a scene via "Replace B-Roll" first, then switch to the ViMax AI tab.');
  }
  const prompt = document.getElementById('vimaxClipPrompt')?.value?.trim();
  if (!prompt) return alert('Enter a scene description for the ViMax Director.');

  const cameraCode = document.getElementById('vimaxCameraCode')?.value || '';
  const statusEl = document.getElementById('vimaxClipStatus');
  const btn = document.getElementById('btnExecVimaxClip');

  statusEl.classList.remove('hidden');
  btn.disabled = true;
  btn.textContent = '⏳ Generating...';

  try {
    const formData = new FormData();
    formData.append('prompt', prompt);
    if (cameraCode) formData.append('camera_code', cameraCode);

    const res = await fetch(`/api/project/${currentRunId}/scene/${targetReplaceSceneId}/generate-ai-clip`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (data.status === 'success') {
      stockModal.classList.add('hidden');
      await loadProject(currentRunId);
    } else {
      alert('AI clip generation failed.');
    }
  } catch (err) {
    alert('ViMax AI generation failed: ' + err);
  } finally {
    statusEl.classList.add('hidden');
    btn.disabled = false;
    btn.textContent = '⚡ Generate Cinematic AI Clip';
  }
}
