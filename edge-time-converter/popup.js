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

// On popup open, check whether the interval is actually running in the tab.
(async () => {
  try {
    const tab = await getActiveTab();
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => !!window.__gmtObserver,
    });
    toggle.checked = results?.[0]?.result ?? false;
    if (toggle.checked) setStatus('Running');
  } catch {
    toggle.checked = false;
  }
})();

toggle.addEventListener('change', async () => {
  const tab = await getActiveTab();
  const enabled = toggle.checked;

  try {
    if (enabled) {
      setStatus('Starting...');
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['start_interval.js'],
      });
      setStatus('Running');
    } else {
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
