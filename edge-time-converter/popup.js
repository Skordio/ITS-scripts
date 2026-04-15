const toggle = document.getElementById('toggleSwitch');
const status = document.getElementById('status');

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function setStatus(text, isError = false) {
  status.className = isError ? 'error' : '';
  status.textContent = text;
}

// Read/write the enabled-tab set directly from storage.
// chrome.storage.session is accessible from all extension contexts, so the
// popup never needs to message the background worker (which may be idle).
const SESSION_KEY = 'gmtEnabledTabs';

async function getEnabledTabs() {
  const result = await chrome.storage.session.get(SESSION_KEY);
  return new Set(result[SESSION_KEY] ?? []);
}

async function saveEnabledTabs(set) {
  await chrome.storage.session.set({ [SESSION_KEY]: [...set] });
}

// On popup open, check storage directly.
(async () => {
  try {
    const tab = await getActiveTab();
    const enabled = await getEnabledTabs();
    toggle.checked = enabled.has(tab.id);
    if (toggle.checked) setStatus('Running');
  } catch {
    toggle.checked = false;
  }
})();

toggle.addEventListener('change', async () => {
  const tab = await getActiveTab();
  const enabled = toggle.checked;

  try {
    const tabs = await getEnabledTabs();

    if (enabled) {
      setStatus('Starting...');
      // Persist state before injecting so a racing onUpdated event sees the
      // correct state if the page happens to reload at the same moment.
      tabs.add(tab.id);
      await saveEnabledTabs(tabs);
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['start_interval.js'],
      });
      setStatus('Running');
    } else {
      // Remove from storage first so the background's onUpdated listener
      // doesn't re-enable the tab while we're in the middle of stopping it.
      tabs.delete(tab.id);
      await saveEnabledTabs(tabs);
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['stop_interval.js'],
      });
      setStatus('Stopped.');
    }
  } catch (err) {
    setStatus('Error: ' + err.message, true);
    toggle.checked = !enabled;
  }
});
