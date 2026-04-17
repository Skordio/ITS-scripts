// Tracks which tab IDs have the converter enabled.
// chrome.storage.session persists across service-worker restarts but is
// cleared when the browser closes — a sensible lifetime for this toggle.
// The popup reads/writes storage directly, so no message-passing is needed.

const SESSION_KEY = 'gmtEnabledTabs';

async function getEnabledTabs() {
  const result = await chrome.storage.session.get(SESSION_KEY);
  return new Set(result[SESSION_KEY] ?? []);
}

async function saveEnabledTabs(set) {
  await chrome.storage.session.set({ [SESSION_KEY]: [...set] });
}

// Re-inject the converter whenever an enabled tab finishes loading a new page.
chrome.tabs.onUpdated.addListener(async (tabId, changeInfo) => {
  if (changeInfo.status !== 'complete') return;
  const enabled = await getEnabledTabs();
  if (!enabled.has(tabId)) return;
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ['start_interval.js'],
    });
  } catch {
    // Silently ignore un-injectable pages (e.g. edge:// / chrome:// URLs).
  }
});

// Remove a tab from the enabled set when it's closed.
chrome.tabs.onRemoved.addListener(async (tabId) => {
  const enabled = await getEnabledTabs();
  if (enabled.delete(tabId)) {
    await saveEnabledTabs(enabled);
  }
});
