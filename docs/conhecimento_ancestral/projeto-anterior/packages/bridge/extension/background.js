const ExtensionState = {
  recording: false,
  steps: [],
};

chrome.runtime.onInstalled.addListener(() => {
  console.log('[TestForge] Background persistente. Estado sobrevive a navegações.');
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  switch (msg.type) {
    case 'getState':
      sendResponse({ state: ExtensionState });
      break;
    case 'setRecording':
      ExtensionState.recording = msg.value;
      if (!msg.value) {
        ExtensionState.lastUrl = sender?.tab?.url || '';
      }
      sendResponse({ ok: true });
      break;
    case 'addStep':
      ExtensionState.steps.push(msg.step);
      sendResponse({ ok: true });
      break;
    case 'clearSteps':
      ExtensionState.steps = [];
      sendResponse({ ok: true });
      break;
    case 'finalizeSteps':
      const finalSteps = [...ExtensionState.steps];
      ExtensionState.steps = [];
      ExtensionState.recording = false;
      sendResponse({ steps: finalSteps });
      break;
  }
  return true;
});
