const recordBtn = document.getElementById('recordBtn');
const assertBtn = document.getElementById('assertBtn');
const finalizeBtn = document.getElementById('finalizeBtn');
const stepCount = document.getElementById('stepCount');
const statusInfo = document.getElementById('statusInfo');

let state = { recording: false, steps: 0 };

function updateUI() {
  recordBtn.textContent = state.recording ? '⏹ Parar' : '⏺ Gravar';
  recordBtn.className = state.recording ? 'recording' : '';
  stepCount.textContent = `${state.steps} passos`;
}

function sendToTab(msg) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, msg).catch(() => {
        statusInfo.textContent = '● Nenhuma página ativa';
      });
    }
  });
}

recordBtn.addEventListener('click', () => {
  if (state.recording) {
    sendToTab({ type: 'recording:stop' });
    state.recording = false;
  } else {
    sendToTab({ type: 'recording:start' });
    state.recording = true;
    state.steps = 0;
  }
  updateUI();
});

assertBtn.addEventListener('click', () => {
  sendToTab({ type: 'assert:suggest', payload: { suggestedAssert: 'visible' } });
});

finalizeBtn.addEventListener('click', () => {
  sendToTab({ type: 'recording:stop' });
  state.recording = false;
  updateUI();
});

// Poll state from background
setInterval(() => {
  chrome.runtime.sendMessage({ type: 'getState' }, (res) => {
    if (res?.state) {
      state.recording = res.state.recording;
      state.steps = res.state.steps?.length || 0;
      updateUI();
      statusInfo.textContent = state.recording ? '● Gravando...' : '● Parado';
    }
  });
}, 1000);

statusInfo.textContent = '● Conectado';
