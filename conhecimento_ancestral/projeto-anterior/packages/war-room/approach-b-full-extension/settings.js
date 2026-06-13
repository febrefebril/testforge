function loadSettings() {
  chrome.storage.local.get({
    bridgePort: '9199',
    browser: 'firefox',
    autoRecord: false,
    captureShadowDOM: false,
  }, (items) => {
    document.getElementById('bridgePort').value = items.bridgePort;
    document.getElementById('browser').value = items.browser;
    document.getElementById('autoRecord').checked = items.autoRecord;
    document.getElementById('captureShadowDOM').checked = items.captureShadowDOM;
  });
}

function saveSettings() {
  chrome.storage.local.set({
    bridgePort: document.getElementById('bridgePort').value,
    browser: document.getElementById('browser').value,
    autoRecord: document.getElementById('autoRecord').checked,
    captureShadowDOM: document.getElementById('captureShadowDOM').checked,
  }, () => {
    const el = document.getElementById('saved');
    el.style.display = 'block';
    setTimeout(() => el.style.display = 'none', 2000);
  });
}

document.addEventListener('DOMContentLoaded', loadSettings);
document.getElementById('saveBtn').addEventListener('click', saveSettings);
