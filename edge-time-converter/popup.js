document.getElementById('convertBtn').addEventListener('click', async () => {
  const status = document.getElementById('status');
  status.className = '';
  status.textContent = 'Converting...';

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });

    const count = results?.[0]?.result ?? 0;
    if (count === 0) {
      status.textContent = 'No matching times found.';
    } else {
      status.textContent = `Converted ${count} time${count !== 1 ? 's' : ''}.`;
    }
  } catch (err) {
    status.className = 'error';
    status.textContent = 'Error: ' + err.message;
  }
});
