// DocStudio Bulk Image Generator Service Worker

chrome.runtime.onInstalled.addListener(() => {
  console.log("[DocStudio Extension] Service worker initialized.");
});

// Manage prompt queue in storage
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "QUEUE_META_AI_PROMPTS") {
    const { jobId, shots } = request;
    chrome.storage.local.set({
      meta_ai_queue: shots,
      meta_ai_job_id: jobId,
      current_prompt_index: 0,
      active_batch: true
    }, () => {
      chrome.action.setBadgeText({ text: String(shots.length) });
      chrome.action.setBadgeBackgroundColor({ color: "#0084ff" });
      sendResponse({ status: "queued", count: shots.length });
    });
    return true;
  }

  if (request.action === "GET_NEXT_PROMPT") {
    chrome.storage.local.get(["meta_ai_queue", "meta_ai_job_id", "current_prompt_index", "active_batch"], (res) => {
      if (!res.active_batch || !res.meta_ai_queue) {
        sendResponse({ hasMore: false });
        return;
      }

      const idx = res.current_prompt_index || 0;
      if (idx >= res.meta_ai_queue.length) {
        chrome.storage.local.set({ active_batch: false });
        chrome.action.setBadgeText({ text: "✓" });
        chrome.action.setBadgeBackgroundColor({ color: "#10b981" });
        sendResponse({ hasMore: false, completed: true });
        return;
      }

      const shot = res.meta_ai_queue[idx];
      const jobId = res.meta_ai_job_id;
      sendResponse({
        hasMore: true,
        shot: shot,
        jobId: jobId,
        index: idx,
        total: res.meta_ai_queue.length
      });
    });
    return true;
  }

  if (request.action === "MARK_PROMPT_DONE") {
    chrome.storage.local.get(["meta_ai_queue", "current_prompt_index"], (res) => {
      const nextIdx = (res.current_prompt_index || 0) + 1;
      chrome.storage.local.set({ current_prompt_index: nextIdx });
      const remaining = Math.max(0, (res.meta_ai_queue ? res.meta_ai_queue.length : 0) - nextIdx);
      if (remaining > 0) {
        chrome.action.setBadgeText({ text: String(remaining) });
      } else {
        chrome.action.setBadgeText({ text: "✓" });
        chrome.action.setBadgeBackgroundColor({ color: "#10b981" });
      }
      sendResponse({ success: true, nextIndex: nextIdx });
    });
    return true;
  }
});
