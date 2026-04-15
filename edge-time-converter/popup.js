const toggle = document.getElementById('toggleSwitch');
const status = document.getElementById('status');

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function storageKey(tabId) {
  return `gmtToggle_${tabId}`;
}

async function setStatus(text, isError = false) {
  status.className = isError ? 'error' : '';
  status.textContent = text;
}

// On popup open, restore toggle state for the current tab.
(async () => {
  const tab = await getActiveTab();
  const key = storageKey(tab.id);
  const result = await chrome.storage.local.get(key);
  toggle.checked = !!result[key];
})();

toggle.addEventListener('change', async () => {
  const tab = await getActiveTab();
  const key = storageKey(tab.id);
  const enabled = toggle.checked;

  await chrome.storage.local.set({ [key]: enabled });

  try {
    if (enabled) {
      setStatus('Starting...');
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['start_interval.js']
      });
      setStatus('Running. Converts every 20s.');
    } else {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['stop_interval.js']
      });
      setStatus('Stopped.');
    }
  } catch (err) {
    setStatus('Error: ' + err.message, true);
    // Revert toggle on failure
    toggle.checked = !enabled;
    await chrome.storage.local.set({ [key]: !enabled });
  }
});
